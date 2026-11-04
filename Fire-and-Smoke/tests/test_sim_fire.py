# SPDX-License-Identifier: GPL-3.0-or-later
"""Simulated Campfire: a real Mantaflow fire that's owned, scoped to itself and cleaned up.

Every check that plays the simulation steps one frame at a time from the first frame,
since Replay only simulates forward, and compares grids with a tolerance.
"""

import os
import sys

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fas_testlib as lib  # noqa: E402

import bpy  # noqa: E402
from fire_and_smoke.effects import presets, sim_fire  # noqa: E402

STATE = {}


def _tagged():
    groups = ("objects", "meshes", "lights", "materials", "actions", "collections")
    return [(g, i.name) for g in groups for i in getattr(bpy.data, g) if lib.C.OWNER_PROP in i.keys()]


def _entry(effect_uuid):
    return next(e for e in lib.scene().fas_effects if e.uuid == effect_uuid)


def _play(to, start=None):
    scene = lib.scene()
    for frame in range(scene.frame_start if start is None else start, to + 1):
        scene.frame_set(frame)


def _grids(entry):
    """Density and flame sums of the evaluated domain: the original holds no grid data."""
    depsgraph = bpy.context.evaluated_depsgraph_get()
    settings = sim_fire.find_modifier(entry.primary.evaluated_get(depsgraph), "DOMAIN").domain_settings
    density, flame = list(settings.density_grid), list(settings.flame_grid)
    return sum(density), (max(flame) if flame else 0.0)


def _close(a, b, tolerance=0.15):
    return abs(a - b) <= tolerance * max(abs(a), abs(b), 1e-6)


def test_create():
    lib.clear_scene()
    lib.add_camera(location=(0.0, -6.0, 1.2), look_at=(0.0, 0.0, 1.0))
    lib.setup_render(width=160, height=90, background=(0.01, 0.01, 0.01))
    scene = lib.scene()
    scene.frame_start, scene.frame_end = 1, 60
    scene.frame_set(1)
    bpy.ops.mesh.primitive_cube_add(size=0.5, location=(3.0, 0.0, 0.25))
    crate = bpy.context.object
    crate.name = "Crate"
    selected = set(bpy.context.selected_objects)
    scene.cursor.location = (0.0, 0.0, 0.0)

    lib.check("it's preset number 8", dict((p[0], p[1]) for p in presets.PRESETS)["SIMULATED_CAMPFIRE"] == 8)
    order = list(presets.DISPLAY_ORDER)
    lib.check("shown straight after Campfire", order.index("SIMULATED_CAMPFIRE") == order.index("CAMPFIRE") + 1)
    lib.check("in the Fire group", presets.group("SIMULATED_CAMPFIRE") == presets.FIRE_GROUP)

    result = bpy.ops.fas.effect_create(preset="SIMULATED_CAMPFIRE")
    lib.check("created", result == {"FINISHED"})
    entry = scene.fas_effects[-1]
    STATE["uuid"] = entry.uuid
    lib.check("a Simulated Fire entry", entry.kind == lib.C.KIND_SIM_FIRE and entry.preset_id == "SIMULATED_CAMPFIRE")
    lib.check("with 0 planes", entry.planes == 0)
    domain, emitter = entry.primary, entry.emitter
    lib.check("the domain is the primary, at the cursor", domain is not None
              and tuple(domain.location) == (0.0, 0.0, 0.0))
    lib.check("at full size with a scale of 1", tuple(domain.scale) == (1.0, 1.0, 1.0)
              and abs(domain.dimensions.z - sim_fire.DOMAIN_SIZE[2]) < 1e-4, str(tuple(domain.dimensions)))
    lib.check("the emitter is the domain's child", emitter is not None and emitter.parent == domain)
    lib.check("and hidden from renders", emitter.hide_render)
    for obj in (domain, emitter):
        lib.check(f"{obj.name} is tagged, with its mesh", lib.C.OWNER_PROP in obj.keys()
                  and lib.C.OWNER_PROP in obj.data.keys())
        lib.check(f"{obj.name} sits in the effect's collection", entry.root_collection in obj.users_collection)
    material = domain.data.materials[0]
    lib.check("the volume material is tagged", lib.C.OWNER_PROP in material.keys())
    tags = {i[lib.C.OWNER_PROP] for g in ("objects", "meshes", "materials", "collections")
            for i in getattr(bpy.data, g) if lib.C.OWNER_PROP in i.keys()}
    lib.check("everything is tagged for one effect", len(tags) == 1, str(tags))

    settings = sim_fire.domain_settings(entry)
    lib.check("a Replay cache", settings.cache_type == "REPLAY")
    lib.check("at 64 divisions", settings.resolution_max == 64)
    lib.check("taking flows and effectors from its own collection",
              settings.fluid_group == entry.root_collection and settings.effector_group == entry.root_collection)
    lib.check("over the timeline", (settings.cache_frame_start, settings.cache_frame_end) == (1, 60))
    lib.check("with no noise pass", not settings.use_noise)
    flow = sim_fire.flow_settings(entry)
    lib.check("the emitter makes smoke and fire", flow.flow_type == "BOTH" and flow.flow_behavior == "INFLOW")

    lib.check("the selection is unchanged", set(bpy.context.selected_objects) == selected
              and bpy.context.view_layer.objects.active == crate)
    lib.check("the selected object is unchanged", not list(crate.modifiers) and lib.C.OWNER_PROP not in crate.keys())
    lib.check("no transparent bounce change is needed", scene.fas_bounce_original == -1)
    STATE["crate"] = crate.name


def test_it_burns():
    entry = _entry(STATE["uuid"])
    _play(30)
    density, flame = _grids(entry)
    lib.info(f"after frames 1 to 30: density sum {density:.1f}, flame max {flame:.3f}")
    lib.check("smoke fills the domain by frame 30", density > 1.0, f"{density:.2f}")
    lib.check("and there's fire", flame > 0.05, f"{flame:.3f}")
    STATE["density"] = density


def test_a_small_cycles_render_isnt_dark():
    pixels = lib.render("CYCLES")
    bright = sum(1 for i in range(0, len(pixels), 4) if pixels[i] > 0.3)
    lib.info(f"Cycles at frame 30: {bright} bright pixels at 160x90")
    lib.check("the fire shows in Cycles", bright >= 20, str(bright))
    STATE["cycles_bright"] = bright


def test_clearing_the_cache_simulates_again():
    entry = _entry(STATE["uuid"])
    data = os.path.join(sim_fire.domain_settings(entry).cache_directory, "data")
    lib.check("playing wrote the cache folder", os.path.isdir(data) and len(os.listdir(data)) > 0)

    def stamps():
        return {name: os.path.getmtime(os.path.join(data, name)) for name in os.listdir(data)}

    scene = lib.scene()
    before = stamps()
    scene.frame_set(1)
    _play(10)
    lib.check("an unchanged replay reads the cache", stamps() == before)
    sim_fire.clear_cache(_entry(STATE["uuid"]))
    scene.frame_set(1)
    _play(10)
    after = stamps()
    rewritten = sum(1 for name, stamp in after.items() if before.get(name) != stamp)
    lib.check("after a clear the next play simulates again", rewritten >= 5, str(rewritten))
    scene.frame_set(1)
    _play(30)


def test_its_own_flows_only():
    scene = lib.scene()
    entry = _entry(STATE["uuid"])
    scene.frame_set(1)
    bpy.ops.fas.effect_create(preset="SIMULATED_CAMPFIRE")
    other = scene.fas_effects[-1].uuid
    # A buyer's own flow right inside the first domain.
    bpy.ops.mesh.primitive_cube_add(size=0.6, location=(0.0, 0.0, 0.4))
    theirs = bpy.context.object
    fluid = theirs.modifiers.new("Fluid", "FLUID")
    fluid.fluid_type = "FLOW"
    fluid.flow_settings.flow_type = "BOTH"
    fluid.flow_settings.flow_behavior = "INFLOW"
    entry = _entry(STATE["uuid"])
    sim_fire.clear_cache(entry)
    scene.frame_set(1)
    _play(30)
    density, _flame = _grids(_entry(STATE["uuid"]))
    lib.info(f"with a second fire and a buyer's flow inside: density sum {density:.1f} (alone {STATE['density']:.1f})")
    lib.check("a second Simulated Campfire and a buyer's flow change nothing in it",
              _close(density, STATE["density"]), f"{density:.1f} against {STATE['density']:.1f}")
    # The control: unscoped, the same domain takes both other flows.
    settings = sim_fire.domain_settings(_entry(STATE["uuid"]))
    settings.fluid_group = None
    sim_fire.clear_cache(_entry(STATE["uuid"]))
    scene.frame_set(1)
    _play(30)
    unscoped, _flame = _grids(_entry(STATE["uuid"]))
    lib.info(f"the same domain unscoped: density sum {unscoped:.1f}")
    lib.check("the control: unscoped, it would take them", unscoped > STATE["density"] * 1.2,
              f"{unscoped:.1f} against {STATE['density']:.1f}")
    settings.fluid_group = _entry(STATE["uuid"]).root_collection
    sim_fire.clear_cache(_entry(STATE["uuid"]))
    bpy.data.objects.remove(theirs)
    bpy.ops.fas.effect_delete(uuid=other)
    lib.check("deleting the second leaves the first", _entry(STATE["uuid"]).primary is not None)
    scene.frame_set(1)


def test_no_fluid_is_refused_plainly():
    original = sim_fire.bpy

    class _NoFluid:
        def __getattr__(self, name):
            return getattr(original, name)

    fake = _NoFluid()
    fake.app = type("App", (), {"build_options": type("B", (), {"fluid": False})()})()
    sim_fire.bpy = fake
    count = len(lib.scene().fas_effects)
    try:
        try:
            result = bpy.ops.fas.effect_create(preset="SIMULATED_CAMPFIRE")
        except RuntimeError as exc:
            result = {"CANCELLED"}
            lib.check("the message is plain", "built without Fluid" in str(exc), str(exc))
    finally:
        sim_fire.bpy = original
    lib.check("refused", result == {"CANCELLED"})
    lib.check("nothing is made", len(lib.scene().fas_effects) == count)
    err = lib.addon.errors.last_error()
    lib.check("with a plain message and no traceback for the buyer",
              err is not None and "built without Fluid" in err["message"], str(err and err["message"]))


def test_delete_cleans_up():
    bpy.ops.fas.effect_delete(uuid=STATE["uuid"])
    lib.check("nothing tagged left", not _tagged(), str(_tagged()))
    crate = bpy.data.objects.get(STATE["crate"])
    lib.check("the buyer's object stays", crate is not None and not list(crate.modifiers))


lib.main(globals())
