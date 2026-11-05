# SPDX-License-Identifier: GPL-3.0-or-later
"""Fire and Smoke from Mesh: a simulated fire that burns from the buyer's mesh, which it
never changes, and that Delete cleans up.

Every check that plays the simulation steps one frame at a time from the first frame,
since Replay only simulates forward.
"""

import os
import sys

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fas_testlib as lib  # noqa: E402

import bpy  # noqa: E402
from fire_and_smoke.effects import plane_stack, presets, sim_fire, sim_mesh_fire, sim_presets  # noqa: E402
from mathutils import Vector  # noqa: E402

PRESET = "SIMULATED_MESH_FIRE"
STATE = {}


def _tagged():
    groups = ("objects", "meshes", "lights", "materials", "node_groups", "actions", "collections")
    return [(g, i.name) for g in groups for i in getattr(bpy.data, g) if lib.C.OWNER_PROP in i.keys()]


def _entry():
    return next(e for e in lib.scene().fas_effects if e.uuid == STATE["uuid"])


def _snapshot(obj):
    """Everything of the buyer's object that the fire must never change."""
    mesh = obj.data
    return {
        "name": obj.name,
        "matrix": [tuple(row) for row in obj.matrix_world],
        "modifiers": [(m.name, m.type) for m in obj.modifiers],
        "constraints": [c.name for c in obj.constraints],
        "custom": sorted(obj.keys()),
        "groups": [(g.name, g.index) for g in obj.vertex_groups],
        "weights": [[(g.group, round(g.weight, 6)) for g in v.groups] for v in mesh.vertices],
        "data": mesh.name,
        "data_custom": sorted(mesh.keys()),
        "vertices": [tuple(round(c, 6) for c in v.co) for v in mesh.vertices],
        "materials": [m.name if m else None for m in mesh.materials],
        "hide": (obj.hide_viewport, obj.hide_render, obj.hide_get(), obj.display_type),
        "visibility": (obj.visible_camera, obj.visible_shadow, obj.visible_diffuse, obj.visible_glossy),
        "parent": obj.parent,
        "collections": sorted(c.name for c in obj.users_collection),
    }


def _play(to):
    scene = lib.scene()
    for frame in range(scene.frame_start, to + 1):
        scene.frame_set(frame)


def _flame(entry):
    """The evaluated domain's flame, summed over its two halves along x."""
    depsgraph = bpy.context.evaluated_depsgraph_get()
    settings = sim_fire.find_modifier(entry.primary.evaluated_get(depsgraph), "DOMAIN").domain_settings
    rx, ry, rz = settings.domain_resolution
    flame = settings.flame_grid
    left = right = 0.0
    for index, value in enumerate(flame):
        if index % rx < rx // 2:
            left += value
        else:
            right += value
    density = sum(settings.density_grid)
    return left, right, density


def _folder(entry):
    return os.path.realpath(bpy.path.abspath(sim_fire.domain_settings(entry).cache_directory))


def test_create():
    lib.clear_scene()
    lib.add_camera(location=(2.0, -7.0, 1.5), look_at=(2.0, 0.0, 1.2))
    lib.setup_render(width=160, height=90, background=(0.01, 0.01, 0.01))
    scene = lib.scene()
    scene.frame_start, scene.frame_end = 1, 60
    scene.frame_set(1)
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=(2.0, 0.0, 0.5))
    crate = bpy.context.object
    crate.name = "My Crate"
    crate.vertex_groups.new(name="Top").add([v.index for v in crate.data.vertices if v.co.z > 0], 1.0, "REPLACE")
    selected = set(bpy.context.selected_objects)
    STATE["crate"] = crate.name
    STATE["before"] = _snapshot(crate)

    numbers = dict((p[0], p[1]) for p in presets.PRESETS)
    lib.check("it's preset number 9", numbers[PRESET] == 9)
    order = list(presets.DISPLAY_ORDER)
    lib.check("shown straight after Burning Object", order.index(PRESET) == order.index("BURNING_OBJECT") + 1)
    lib.check("in the Fire group", presets.group(PRESET) == presets.FIRE_GROUP)
    lib.check("its label", presets.label(PRESET) == "Fire and Smoke from Mesh")

    result = bpy.ops.fas.effect_create(preset=PRESET)
    lib.check("created", result == {"FINISHED"})
    entry = scene.fas_effects[-1]
    STATE["uuid"] = entry.uuid
    lib.check("a Fire and Smoke from Mesh entry", entry.kind == lib.C.KIND_SIM_MESH_FIRE
              and entry.preset_id == PRESET, entry.kind)
    lib.check("it records the mesh it burns", entry.source == crate)
    lib.check("with 0 planes", entry.planes == 0)
    lib.check("starting from the Campfire preset", entry.sim_preset == sim_presets.CAMPFIRE
              and not sim_presets.is_modified(entry))

    domain, emitter, light = entry.primary, entry.emitter, entry.light
    bpy.context.view_layer.update()
    follow = [c for c in domain.constraints if c.type == "COPY_LOCATION"]
    lib.check("the domain follows the mesh's moves", len(follow) == 1 and follow[0].target == crate
              and follow[0].use_offset and not list(c for c in domain.constraints if c.type != "COPY_LOCATION"))
    lib.check("the domain has a scale of 1", tuple(domain.scale) == (1.0, 1.0, 1.0))
    low, high = sim_mesh_fire.world_bounds(domain)
    mesh_low, mesh_high = sim_mesh_fire.world_bounds(crate)
    lib.check("the box holds the mesh with room around it",
              all(low[i] < mesh_low[i] - 0.3 and high[i] > mesh_high[i] + 0.3 for i in (0, 1))
              and low.z <= mesh_low.z and high.z > mesh_high.z + 2.0,
              f"box {tuple(low)} to {tuple(high)}, mesh {tuple(mesh_low)} to {tuple(mesh_high)}")
    lib.check("the emitter and light are the domain's children", emitter.parent == domain and light.parent == domain)
    lib.check("the emitter is hidden from renders", emitter.hide_render)
    lib.check("the light is above the mesh", light.matrix_world.translation.z > mesh_high.z)
    copy = next((m for m in emitter.modifiers if m.type == "NODES"), None)
    lib.check("the emitter copies the mesh live", copy is not None
              and plane_stack.get_input(copy, sim_mesh_fire.SOURCE_INPUT) == crate)
    lib.check("before its flow", [m.type for m in emitter.modifiers] == ["NODES", "FLUID"])
    lib.check("the emitter's own mesh is empty", len(emitter.data.vertices) == 0)
    evaluated = emitter.evaluated_get(bpy.context.evaluated_depsgraph_get()).data
    lib.check("and it evaluates to the mesh, where it is", len(evaluated.vertices) == len(crate.data.vertices)
              and (emitter.matrix_world @ evaluated.vertices[0].co - crate.matrix_world @ crate.data.vertices[0].co).length
              < 1e-4)
    for obj in (domain, emitter, light):
        lib.check(f"{obj.name} is tagged, with its data", lib.C.OWNER_PROP in obj.keys()
                  and lib.C.OWNER_PROP in obj.data.keys())
        lib.check(f"{obj.name} sits in the effect's collection", entry.root_collection in obj.users_collection)
    lib.check("the copy's node tree is tagged", lib.C.OWNER_PROP in copy.node_group.keys())
    tags = {i[lib.C.OWNER_PROP] for g in ("objects", "meshes", "materials", "node_groups", "lights", "actions",
                                          "collections")
            for i in getattr(bpy.data, g) if lib.C.OWNER_PROP in i.keys()}
    lib.check("everything is tagged for one effect", len(tags) == 1, str(tags))

    settings = sim_fire.domain_settings(entry)
    lib.check("a Replay cache at 64 divisions", settings.cache_type == "REPLAY" and settings.resolution_max == 64)
    lib.check("taking flows and effectors from its own collection",
              settings.fluid_group == entry.root_collection and settings.effector_group == entry.root_collection)
    lib.check("over the timeline", (settings.cache_frame_start, settings.cache_frame_end) == (1, 60))
    flow = sim_fire.flow_settings(entry)
    lib.check("the emitter makes smoke and fire from its surface", flow.flow_type == "BOTH"
              and flow.flow_behavior == "INFLOW" and flow.flow_source == "MESH")

    lib.check("the selection is unchanged", set(bpy.context.selected_objects) == selected
              and bpy.context.view_layer.objects.active == crate)
    lib.check("the mesh is unchanged by Create", _snapshot(crate) == STATE["before"])


def test_it_burns_all_over():
    entry = _entry()
    _play(30)
    left, right, density = _flame(entry)
    lib.info(f"after frames 1 to 30: flame {left:.1f} left, {right:.1f} right, density {density:.1f}")
    lib.check("smoke fills the domain", density > 1.0, f"{density:.2f}")
    lib.check("there's fire", left + right > 1.0, f"{left + right:.2f}")
    lib.check("on both sides of the mesh", min(left, right) > 0.4 * max(left, right), f"{left:.1f} / {right:.1f}")


def test_a_small_cycles_render_isnt_dark():
    pixels = lib.render("CYCLES")
    bright = sum(1 for i in range(0, len(pixels), 4) if pixels[i] > 0.3)
    lib.info(f"Cycles at frame 30: {bright} bright pixels at 160x90")
    lib.check("the fire shows in Cycles", bright >= 20, str(bright))


def test_the_mesh_is_unchanged_after_playing():
    lib.check("the mesh is unchanged", _snapshot(bpy.data.objects[STATE["crate"]]) == STATE["before"])


def test_it_refuses_plainly():
    count = len(lib.scene().fas_effects)
    before = set(_tagged())
    for what, active, words in (("nothing selected", None, "Select a mesh"),
                                ("one of its own parts", _entry().primary, "part of an effect")):
        bpy.context.view_layer.objects.active = active
        try:
            result = bpy.ops.fas.effect_create(preset=PRESET)
        except RuntimeError as exc:
            result = {"CANCELLED"}
            lib.check(f"refuses {what} plainly", words in str(exc), str(exc)[:120])
        lib.check(f"refuses {what}", result == {"CANCELLED"})
    lib.check("nothing half-built is left", len(lib.scene().fas_effects) == count and set(_tagged()) == before)
    bpy.context.view_layer.objects.active = bpy.data.objects[STATE["crate"]]


def test_delete_cleans_up():
    entry = _entry()
    folder = _folder(entry)
    lib.check("the cache folder exists before Delete", os.path.isdir(folder))
    bpy.ops.fas.effect_delete(uuid=STATE["uuid"])
    lib.check("nothing tagged left", not _tagged(), str(_tagged()))
    lib.check("Delete removes the effect's cache folder", not os.path.exists(folder), folder)
    crate = bpy.data.objects.get(STATE["crate"])
    lib.check("the mesh stays, exactly as it was", crate is not None and _snapshot(crate) == STATE["before"])
    lib.check("and it's still in the scene", crate.name in lib.scene().objects)


def test_a_moved_mesh_gets_a_box_where_it_is():
    """The box is placed from the mesh's world bounds, whatever its origin and scale."""
    crate = bpy.data.objects[STATE["crate"]]
    crate.location = (-3.0, 1.0, 2.0)
    crate.scale = (2.0, 1.0, 0.5)
    bpy.context.view_layer.update()
    bpy.ops.fas.effect_create(preset=PRESET)
    entry = lib.scene().fas_effects[-1]
    bpy.context.view_layer.update()
    low, high = sim_mesh_fire.world_bounds(entry.primary)
    mesh_low, mesh_high = sim_mesh_fire.world_bounds(crate)
    centre, mesh_centre = (low + high) * 0.5, (mesh_low + mesh_high) * 0.5
    lib.check("the box is centred on the mesh", (Vector((centre.x, centre.y)) - Vector((mesh_centre.x, mesh_centre.y))
                                                 ).length < 1e-4, f"{tuple(centre)} / {tuple(mesh_centre)}")
    lib.check("and starts at its foot", abs(low.z - mesh_low.z) < 0.2 * (mesh_high - mesh_low).length,
              f"{low.z:.3f} / {mesh_low.z:.3f}")
    bpy.ops.fas.effect_delete(uuid=entry.uuid)
    lib.check("and it deletes cleanly", not _tagged(), str(_tagged()))


lib.main(globals())
