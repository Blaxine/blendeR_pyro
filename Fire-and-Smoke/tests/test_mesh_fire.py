# SPDX-License-Identifier: GPL-3.0-or-later
"""Fire on a mesh: follows it, never changes it, and copes with it going away."""

import os
import sys
import time

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fas_testlib as lib  # noqa: E402

import bpy  # noqa: E402
from fire_and_smoke.effects import mesh_fire  # noqa: E402
from mathutils import Vector  # noqa: E402

STATE = {}


def _snapshot(obj):
    return {
        "modifiers": [m.name for m in obj.modifiers],
        "constraints": [c.name for c in obj.constraints],
        "custom": sorted(obj.keys()),
        "data": obj.data.name,
        "data_custom": sorted(obj.data.keys()),
        "vertices": len(obj.data.vertices),
        "first_vertex": tuple(obj.data.vertices[0].co),
        "materials": [m.name if m else None for m in obj.data.materials],
        "hide": (obj.hide_viewport, obj.hide_render, obj.display_type),
        "visibility": (obj.visible_camera, obj.visible_shadow),
        "parent": obj.parent,
        "collections": sorted(c.name for c in obj.users_collection),
    }


def _cube(size=2.0, location=(4.0, 0.0, 1.0), name="My Crate"):
    bpy.ops.mesh.primitive_cube_add(size=size, location=location)
    obj = bpy.context.object
    obj.name = name
    return obj


def _tagged():
    groups = ("objects", "meshes", "lights", "materials", "node_groups", "actions", "collections")
    return [i.name for g in groups for i in getattr(bpy.data, g) if lib.C.OWNER_PROP in i.keys()]


def test_setup():
    lib.clear_scene()
    lib.add_camera()
    lib.setup_render()
    STATE["source"] = _cube()
    STATE["before"] = _snapshot(STATE["source"])
    result = bpy.ops.fas.mesh_fire_create()
    lib.check("it's created", result == {"FINISHED"})
    entry = lib.scene().fas_effects[-1]
    STATE["uuid"] = entry.uuid
    lib.check("it records its source", entry.source == STATE["source"] and entry.kind == lib.C.KIND_MESH_FIRE)
    bpy.context.view_layer.update()
    modifier = entry.primary.modifiers[0]
    lib.check("no node warnings", not list(modifier.node_warnings), str([w.message for w in modifier.node_warnings]))
    count = lib.instance_count(entry.primary)
    lib.check("planes sit on the mesh", count > 0, str(count))
    lib.check("the estimate covers what was made", entry.planes >= count, f"{entry.planes} / {count}")
    lib.check("the limit is above the planes", lib.scene().cycles.transparent_max_bounces > entry.planes)


def test_source_is_untouched():
    lib.check("the source is unchanged during", _snapshot(STATE["source"]) == STATE["before"])


def _plane_centre(obj):
    depsgraph = bpy.context.evaluated_depsgraph_get()
    points = [inst.matrix_world.translation.copy() for inst in depsgraph.object_instances
              if inst.is_instance and inst.parent and inst.parent.original == obj]
    return sum(points, Vector()) / len(points)


def test_follows_the_source():
    entry = lib.scene().fas_effects[-1]
    before = _plane_centre(entry.primary)
    light_before = entry.light.matrix_world.translation.copy()
    STATE["source"].location.x += 3.0
    bpy.context.view_layer.update()
    after = _plane_centre(entry.primary)
    # Planes also stand off towards the viewer, so the angle to it shifts them a little.
    lib.check("planes moved with it", abs((after - before).x - 3.0) < 0.3, str(after - before))
    lib.check("the light moved with it", abs((entry.light.matrix_world.translation - light_before).x - 3.0) < 1e-3)
    STATE["source"].location.x -= 3.0
    bpy.context.view_layer.update()
    STATE["before"] = _snapshot(STATE["source"])


def test_moves_with_no_bake():
    lib.scene().frame_set(10)
    a = lib.render(lib.eevee_id())
    lib.scene().frame_set(30)
    b = lib.render(lib.eevee_id())
    lib.check("frames differ", lib.mean_diff(a, b) > 1e-4, f"{lib.mean_diff(a, b):.5f}")


def test_refuses_with_a_plain_message():
    bpy.context.view_layer.objects.active = None
    try:
        bpy.ops.fas.mesh_fire_create()
        lib.check("refuses with nothing selected", False)
    except RuntimeError as exc:
        lib.check("refuses with nothing selected", "Select a mesh" in str(exc), str(exc)[:100])
    lib.check("nothing half-built is left", len(lib.scene().fas_effects) == 1)


def test_refuses_its_own_parts():
    entry = lib.scene().fas_effects[-1]
    problem = mesh_fire.source_problem(entry.primary)
    lib.check("won't burn an effect's own object", problem is not None and "your own" in problem, str(problem))


def test_density_limits():
    bpy.ops.mesh.primitive_grid_add(x_subdivisions=500, y_subdivisions=500, size=4.0, location=(0, 8, 0))
    dense = bpy.context.object
    dense.name = "Dense"
    count = len(dense.data.polygons)
    lib.check("a dense-but-allowed mesh passes", mesh_fire.source_problem(dense) is None, str(count))
    bpy.ops.fas.mesh_fire_create()
    uuid = lib.scene().fas_effects[-1].uuid
    bpy.context.view_layer.update()
    start = time.perf_counter()
    for frame in range(1, 11):
        lib.scene().frame_set(frame)
    lib.info(f"{count:,} faces: {(time.perf_counter() - start) * 100:.1f} ms per frame")
    bpy.ops.fas.effect_delete(uuid=uuid)
    mesh = dense.data
    bpy.data.objects.remove(dense)
    bpy.data.meshes.remove(mesh)
    bpy.ops.mesh.primitive_grid_add(x_subdivisions=40, y_subdivisions=40, location=(0, 8, 0))
    big = bpy.context.object
    limit = mesh_fire.MAX_FACES
    mesh_fire.MAX_FACES = 1000
    problem = mesh_fire.source_problem(big)
    mesh_fire.MAX_FACES = limit
    lib.check("past the limit it says so", problem is not None and "over the limit" in problem, str(problem))
    mesh = big.data
    bpy.data.objects.remove(big)
    bpy.data.meshes.remove(mesh)


def test_source_deleted():
    entry = lib.scene().fas_effects[-1]
    uuid = entry.uuid
    primary = entry.primary
    source = STATE.pop("source")
    bpy.data.objects.remove(source)
    bpy.context.view_layer.update()
    entry = next(e for e in lib.scene().fas_effects if e.uuid == uuid)
    lib.check("it knows the source is gone", mesh_fire.is_missing_source(entry))
    lib.check("planes are gone", lib.instance_count(primary) == 0, str(lib.instance_count(primary)))
    lib.check("no node errors", not [w for w in primary.modifiers[0].node_warnings if w.type == "ERROR"])
    lib.scene().frame_set(12)
    lib.check("Delete still works", bpy.ops.fas.effect_delete(uuid=uuid) == {"FINISHED"})
    lib.check("clean afterwards", not _tagged(), str(_tagged()))


def test_delete_leaves_the_source():
    source = _cube(name="Second Crate")
    before = _snapshot(source)
    bpy.ops.fas.mesh_fire_create()
    uuid = lib.scene().fas_effects[-1].uuid
    bpy.ops.fas.effect_delete(uuid=uuid)
    lib.check("the source survives Delete, unchanged", _snapshot(source) == before)
    lib.check("nothing tagged left", not _tagged(), str(_tagged()))


lib.main(globals())
