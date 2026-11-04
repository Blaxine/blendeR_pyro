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
from fire_and_smoke.core import cache_folder  # noqa: E402
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


def _folder(entry):
    return os.path.realpath(bpy.path.abspath(sim_fire.domain_settings(entry).cache_directory))


def _under(path, root):
    path, root = os.path.normcase(os.path.realpath(path)), os.path.normcase(os.path.realpath(root))
    return os.path.commonpath([path, root]) == root


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
    folder = settings.cache_directory
    lib.check("unsaved, the cache lies in the session temp folder", os.path.isabs(folder)
              and _under(folder, bpy.app.tempdir), folder)
    lib.check("in fas_cache, under the effect's own uuid", os.path.basename(folder) == entry.uuid
              and os.path.basename(os.path.dirname(folder)) == "fas_cache", folder)
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


def _bottom_red(pixels, width=160, height=90):
    """Mean red of the bottom quarter, where the ground in front of the fire is."""
    rows = height // 4
    values = [pixels[(y * width + x) * 4] for y in range(rows) for x in range(width)]
    return sum(values) / len(values)


def test_the_light():
    scene = lib.scene()
    entry = _entry(STATE["uuid"])
    domain, light = entry.primary, entry.light
    owner = lib.C.OWNER_PROP
    lib.check("it has a fire light, the domain's child", light is not None and light.parent == domain)
    lib.check("with its light, data and action tagged", owner in light.keys() and owner in light.data.keys()
              and owner in light.data.animation_data.action.keys())
    lib.check("at flame height", 0.2 < light.location.z < 1.0, str(light.location.z))
    lib.check("Real is the default", entry.light_mode == "REAL" and not light.hide_render)
    lib.check("Real hides the domain from diffuse and glossy rays",
              not domain.visible_diffuse and not domain.visible_glossy)
    lib.check("its smoke casts no shadows", not domain.visible_shadow)
    lib.check("the entry knows the light's energy", entry.base_energy > 0.0)
    energies = []
    for frame in (5, 9, 13, 17, 21):
        scene.frame_set(frame)
        energies.append(round(light.data.energy, 3))
    lib.check("the light's energy changes over frames, with no Python running", len(set(energies)) > 2, str(energies))

    bpy.ops.mesh.primitive_plane_add(size=20.0)
    ground = bpy.context.object
    scene.frame_set(1)
    _play(30)
    light.hide_render = True
    dark = _bottom_red(lib.render("CYCLES"))
    light.hide_render = False
    entry = _entry(STATE["uuid"])
    entry.light_mode = "EMISSIVE"
    bpy.context.view_layer.update()
    lib.check("Emissive turns the light off", light.hide_render and light.hide_viewport)
    lib.check("and lets the flames light the scene", domain.visible_diffuse and domain.visible_glossy)
    emissive = _bottom_red(lib.render("CYCLES"))
    _entry(STATE["uuid"]).light_mode = "REAL"
    real = _bottom_red(lib.render("CYCLES"))
    lib.info(f"ground red in Cycles: Real with the light off {dark:.4f}, Emissive {emissive:.4f}, Real {real:.4f}")
    lib.check("in Cycles, Emissive lights the ground where Real with the light off doesn't",
              emissive > dark * 1.1 + 0.002, f"{emissive:.4f} against {dark:.4f}")
    lib.check("and Real's light lights it", real > dark * 1.1 + 0.002, f"{real:.4f} against {dark:.4f}")
    bpy.data.objects.remove(ground)
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
    folder = _folder(_entry(STATE["uuid"]))
    lib.check("the cache folder exists before Delete", os.path.isdir(folder))
    bpy.ops.fas.effect_delete(uuid=STATE["uuid"])
    lib.check("nothing tagged left", not _tagged(), str(_tagged()))
    lib.check("Delete removes the effect's cache folder", not os.path.exists(folder), folder)
    lib.check("and leaves fas_cache itself", os.path.isdir(os.path.dirname(folder)))
    crate = bpy.data.objects.get(STATE["crate"])
    lib.check("the buyer's object stays", crate is not None and not list(crate.modifiers))


def _make(path):
    os.makedirs(path, exist_ok=True)
    with open(os.path.join(path, "keep.txt"), "w") as fh:
        fh.write("the buyer's")
    return path


def test_the_path_check_keeps_everything_else():
    scene = lib.scene()
    bpy.ops.fas.effect_create(preset="SIMULATED_CAMPFIRE")
    entry = scene.fas_effects[-1]
    effect_uuid = entry.uuid
    temp = bpy.app.tempdir
    cases = {
        "a folder with another name": os.path.join(temp, "fas_cache", "not-" + effect_uuid),
        "a folder not inside fas_cache": os.path.join(temp, "elsewhere", effect_uuid),
        "a folder outside both roots": os.path.join(lib.WORKDIR, "outside", "fas_cache", effect_uuid),
    }
    for what, path in cases.items():
        lib.check(f"the check refuses {what}", not cache_folder.removable(path, effect_uuid), path)
    lib.check("the check accepts the effect's own folder",
              cache_folder.removable(cache_folder.temp_path(effect_uuid), effect_uuid))
    lib.check("and refuses it for another effect",
              not cache_folder.removable(cache_folder.temp_path(effect_uuid), "0" * 32))
    lib.check("and refuses fas_cache itself", not cache_folder.removable(os.path.join(temp, "fas_cache"), "fas_cache"))
    for what, path in cases.items():
        _make(path)
        sim_fire.domain_settings(_entry(effect_uuid)).cache_directory = path
        _play(3)
    bpy.ops.fas.effect_delete(uuid=effect_uuid)
    for what, path in cases.items():
        lib.check(f"Delete never removes {what}", os.path.isfile(os.path.join(path, "keep.txt")), path)
    lib.check("nothing tagged left", not _tagged(), str(_tagged()))
    lib.scene().frame_set(1)


def test_saving_puts_the_cache_beside_the_file():
    scene = lib.scene()
    scene.frame_set(1)
    bpy.ops.fas.effect_create(preset="SIMULATED_CAMPFIRE")
    effect_uuid = scene.fas_effects[-1].uuid
    STATE["saved_uuid"] = effect_uuid
    _play(3)
    temp_folder = _folder(_entry(effect_uuid))
    lib.check("unsaved, playing writes the temp folder", os.path.isdir(temp_folder))
    folder = os.path.join(lib.WORKDIR, "first")
    os.makedirs(folder, exist_ok=True)
    path = os.path.join(folder, "campfire.blend")
    bpy.ops.wm.save_as_mainfile(filepath=path)
    settings = sim_fire.domain_settings(_entry(effect_uuid))
    lib.check("saving re-points it beside the file", settings.cache_directory == f"//fas_cache/{effect_uuid}",
              settings.cache_directory)
    lib.check("and the old folder stays", os.path.isdir(temp_folder))
    lib.scene().frame_set(1)
    _play(5)
    beside = os.path.join(folder, "fas_cache", effect_uuid)
    lib.check("the next play writes fas_cache/<uuid> beside the .blend", os.path.isdir(beside), str(os.listdir(folder)))
    density, _flame = _grids(_entry(effect_uuid))
    lib.check("and it still burns", density > 0.1, f"{density:.2f}")

    bpy.ops.wm.open_mainfile(filepath=path)
    entry = _entry(effect_uuid)
    lib.check("the saved file stores the path beside it",
              sim_fire.domain_settings(entry).cache_directory == f"//fas_cache/{effect_uuid}",
              sim_fire.domain_settings(entry).cache_directory)

    other = os.path.join(lib.WORKDIR, "second")
    os.makedirs(other, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(other, "moved.blend"))
    lib.check("Save As to another folder re-points it there",
              sim_fire.domain_settings(_entry(effect_uuid)).cache_directory == f"//fas_cache/{effect_uuid}"
              and _under(_folder(_entry(effect_uuid)), other), _folder(_entry(effect_uuid)))
    lib.check("and the first folder stays where it was", os.path.isdir(beside))
    bpy.ops.wm.open_mainfile(filepath=os.path.join(other, "moved.blend"))
    lib.check("reopened, it points beside the moved file",
              _under(_folder(_entry(effect_uuid)), other), _folder(_entry(effect_uuid)))
    lib.scene().frame_set(1)
    _play(3)
    moved = _folder(_entry(effect_uuid))
    lib.check("where the next play writes", os.path.isdir(moved))
    bpy.ops.fas.effect_delete(uuid=effect_uuid)
    lib.check("Delete removes the folder beside the file", not os.path.exists(moved))
    lib.check("and leaves the one beside the first file, outside this file's folder", os.path.isdir(beside))
    lib.check("nothing tagged left", not _tagged(), str(_tagged()))


lib.main(globals())
