# SPDX-License-Identifier: GPL-3.0-or-later
"""Fire and Smoke from Mesh's Burn From: fire from the whole mesh or one vertex group,
chosen by name, as strongly as the group's weights.

The mesh is a flat 2 x 1 m grid centred in its box, so the box's left half holds the
grid's left half.  "Left" covers x < 0 at weight 1.  Every check that plays steps one
frame at a time from the first frame, since Replay only simulates forward.
"""

import os
import sys

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fas_testlib as lib  # noqa: E402

import bpy  # noqa: E402
from fire_and_smoke.effects import sim_fire, sim_mesh_fire, sim_presets  # noqa: E402

PRESET = "SIMULATED_MESH_FIRE"
FRAMES = 20
STATE = {}


def _entry():
    return next(e for e in lib.scene().fas_effects if e.uuid == STATE["uuid"])


def _grid():
    return bpy.data.objects[STATE["grid"]]


def _groups(obj):
    return [g.name for g in obj.vertex_groups]


def _weights(obj):
    return [(g.name, g.index) for g in obj.vertex_groups], \
           [[(g.group, round(g.weight, 6)) for g in v.groups] for v in obj.data.vertices]


def _flame():
    """The flame in the box's left and right halves, after playing from the first frame."""
    scene = lib.scene()
    for frame in range(scene.frame_start, FRAMES + 1):
        scene.frame_set(frame)
    depsgraph = bpy.context.evaluated_depsgraph_get()
    settings = sim_fire.find_modifier(_entry().primary.evaluated_get(depsgraph), "DOMAIN").domain_settings
    rx = settings.domain_resolution[0]
    left = right = 0.0
    for index, value in enumerate(settings.flame_grid):
        if index % rx < rx // 2:
            left += value
        else:
            right += value
    scene.frame_set(1)
    return left, right


def _counting_clears(change):
    original = sim_fire.clear_cache
    cleared = []
    sim_fire.clear_cache = lambda entry: (cleared.append(entry.uuid), original(entry))
    try:
        change()
    finally:
        sim_fire.clear_cache = original
    return cleared.count(STATE["uuid"])


def _synced():
    entry = _entry()
    return _groups(entry.emitter) == _groups(_grid())


def _burns_left_only(what):
    left, right = _flame()
    lib.info(f"{what}: flame {left:.1f} left, {right:.1f} right")
    lib.check(f"{what}: only the left burns", left > 1.0 and left >= 20.0 * right, f"{left:.1f} / {right:.1f}")


def test_setup():
    lib.clear_scene()
    scene = lib.scene()
    scene.frame_start, scene.frame_end = 1, 40
    scene.frame_set(1)
    nx, ny = 21, 11
    verts = [(-1 + 2 * i / (nx - 1), -0.5 + j / (ny - 1), 0.1) for j in range(ny) for i in range(nx)]
    faces = [(j * nx + i, j * nx + i + 1, (j + 1) * nx + i + 1, (j + 1) * nx + i)
             for j in range(ny - 1) for i in range(nx - 1)]
    mesh = bpy.data.meshes.new("Probe Grid")
    mesh.from_pydata(verts, [], faces)
    grid = bpy.data.objects.new("Probe Grid", mesh)
    scene.collection.objects.link(grid)
    everything = list(range(len(verts)))
    left = [k for k, v in enumerate(verts) if v[0] < -0.05]
    right = [k for k, v in enumerate(verts) if v[0] > 0.05]
    grid.vertex_groups.new(name="Other").add(everything, 0.3, "REPLACE")
    grid.vertex_groups.new(name="Left").add(left, 1.0, "REPLACE")
    # Weight 1 on the left, 0.5 on the right.
    half = grid.vertex_groups.new(name="Half")
    half.add(left, 1.0, "REPLACE")
    half.add(right, 0.5, "REPLACE")
    grid.vertex_groups.new(name="Nothing").add(everything, 0.0, "REPLACE")
    bpy.context.view_layer.objects.active = grid
    grid.select_set(True)
    STATE["grid"] = grid.name
    STATE["before"] = _weights(grid)

    result = bpy.ops.fas.effect_create(preset=PRESET)
    lib.check("created", result == {"FINISHED"})
    entry = scene.fas_effects[-1]
    STATE["uuid"] = entry.uuid
    lib.check("it starts on Whole Mesh", entry.burn_from == ""
              and entry.burn_from_choice == sim_mesh_fire.WHOLE_MESH)
    lib.check("the emitter's groups mirror the mesh's, in order", _synced(), str(_groups(entry.emitter)))
    lib.check("the flow uses no group", sim_fire.flow_settings(entry).density_vertex_group == "")
    items = [item[1] for item in sim_mesh_fire.burn_from_items(entry)]
    lib.check("the menu is Whole Mesh, then the mesh's groups", items == ["Whole Mesh", "Other", "Left", "Half",
                                                                          "Nothing"], str(items))
    lib.check("the mesh is unchanged by Create", _weights(grid) == STATE["before"])


def test_whole_mesh_burns_both_halves():
    left, right = _flame()
    lib.info(f"Whole Mesh: flame {left:.1f} left, {right:.1f} right")
    lib.check("Whole Mesh burns both halves", left > 1.0 and min(left, right) > 0.4 * max(left, right),
              f"{left:.1f} / {right:.1f}")
    STATE["whole"] = left + right


def test_choosing_a_group():
    entry = _entry()

    def choose():
        entry.burn_from_choice = "Left"
    clears = _counting_clears(choose)
    lib.check("choosing Left stores its name", entry.burn_from == "Left" and entry.burn_from_choice == "Left",
              entry.burn_from)
    lib.check("the flow burns from Left", sim_fire.flow_settings(entry).density_vertex_group == "Left")
    lib.check("and it simulates again", clears >= 1, str(clears))
    lib.check("Burn From isn't part of the preset", not sim_presets.is_modified(entry))
    _burns_left_only("Left")
    lib.check("the mesh's groups are unchanged", _weights(_grid()) == STATE["before"])


def test_other_groups_dont_move_the_fire():
    grid = _grid()
    bpy.context.view_layer.objects.active = grid

    def add_one_before():
        grid.vertex_groups.new(name="Extra")
        grid.vertex_groups.active_index = len(grid.vertex_groups) - 1
        for _ in range(len(grid.vertex_groups) - 1):
            bpy.ops.object.vertex_group_move(direction="UP")
        bpy.context.view_layer.update()
    clears = _counting_clears(add_one_before)
    lib.check("a group added before Left is first", _groups(grid)[0] == "Extra", str(_groups(grid)))
    lib.check("the emitter follows the mesh's list", _synced(), str(_groups(_entry().emitter)))
    lib.check("the flow still burns from Left", sim_fire.flow_settings(_entry()).density_vertex_group == "Left")
    lib.check("and it simulates again", clears >= 1, str(clears))
    _burns_left_only("after adding a group before Left")

    grid.vertex_groups.remove(grid.vertex_groups["Other"])
    bpy.context.view_layer.update()
    grid.vertex_groups.active_index = grid.vertex_groups.find("Left")
    bpy.ops.object.vertex_group_move(direction="UP")
    bpy.context.view_layer.update()
    lib.check("Other is deleted and Left moved first", _groups(grid)[:2] == ["Left", "Extra"], str(_groups(grid)))
    lib.check("the emitter follows again", _synced(), str(_groups(_entry().emitter)))
    lib.check("the flow still burns from Left", sim_fire.flow_settings(_entry()).density_vertex_group == "Left")
    lib.check("the menu shows Left where it is now", _entry().burn_from_choice == "Left"
              and [i[1] for i in sim_mesh_fire.burn_from_items(_entry())][1] == "Left")
    _burns_left_only("after deleting a group and reordering")
    STATE["before"] = _weights(grid)


def test_a_sync_writes_only_what_differs():
    entry = _entry()
    clears = _counting_clears(lambda: [bpy.context.view_layer.update() for _ in range(3)])
    lib.check("an update with nothing changed doesn't simulate again", clears == 0, str(clears))
    lib.check("nor write anything", not sim_mesh_fire.sync(entry))


def test_presets_keep_burn_from():
    entry = _entry()
    for preset in (sim_presets.CANDLE_FIRE, sim_presets.CAMPFIRE):
        entry.sim_preset_choice = preset
        bpy.ops.fas.apply_sim_preset(uuid=entry.uuid)
    lib.check("Apply keeps Burn From", entry.burn_from == "Left"
              and sim_fire.flow_settings(entry).density_vertex_group == "Left")


def test_weights_set_the_strength():
    entry = _entry()
    entry.burn_from_choice = "Half"
    full, half = _flame()
    lib.info(f"Half (1 left, 0.5 right): flame {full:.1f} left, {half:.1f} right")
    lib.check("a half at weight 0.5 burns less than a half at 1", half < 0.8 * full, f"{half:.1f} / {full:.1f}")
    lib.check("but still burns", half > 0.02 * full, f"{half:.1f} / {full:.1f}")
    entry.burn_from_choice = "Nothing"
    left, right = _flame()
    lib.info(f"Nothing (weight 0): flame {left:.2f} left, {right:.2f} right")
    lib.check("weight 0 burns nothing", left + right < 0.01 * STATE["whole"], f"{left + right:.2f}")


def test_back_to_whole_mesh():
    entry = _entry()
    entry.burn_from_choice = sim_mesh_fire.WHOLE_MESH
    lib.check("Whole Mesh clears the name", entry.burn_from == ""
              and sim_fire.flow_settings(entry).density_vertex_group == "")
    left, right = _flame()
    lib.check("and both halves burn again", left > 1.0 and min(left, right) > 0.4 * max(left, right),
              f"{left:.1f} / {right:.1f}")
    lib.check("the mesh's groups are unchanged throughout", _weights(_grid()) == STATE["before"])


def test_delete_cleans_up():
    bpy.ops.fas.effect_delete(uuid=STATE["uuid"])
    owned = [o.name for o in bpy.data.objects if lib.C.OWNER_PROP in o.keys()]
    lib.check("nothing owned is left", not owned, str(owned))
    lib.check("the mesh keeps its groups", _weights(_grid()) == STATE["before"])


lib.main(globals())
