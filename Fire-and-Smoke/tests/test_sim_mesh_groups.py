# SPDX-License-Identifier: GPL-3.0-or-later
"""Fire and Smoke from Mesh's Burn From: fire from the whole mesh or one vertex group,
chosen by name, as strongly as the group's weights.  A chosen group or a mesh that's
gone stops the fire and says so in the box.

The mesh is a flat 2 x 1 m grid centred in its box, so the box's left half holds the
grid's left half.  "Left" covers x < 0 at weight 1.  Every check that plays steps one
frame at a time from the first frame, since Replay only simulates forward.
"""

import os
import sys
import time

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fas_testlib as lib  # noqa: E402

import bpy  # noqa: E402
from fire_and_smoke.effects import mesh_fire, sim_fire, sim_mesh_fire, sim_presets  # noqa: E402
from fire_and_smoke.ui import panel  # noqa: E402

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


def _weight_sums(mesh):
    sums = {}
    for vertex in mesh.vertices:
        for group in vertex.groups:
            sums[group.group] = round(sums.get(group.group, 0.0) + group.weight, 2)
    return sums


def _burning(entry):
    modifier = sim_fire.find_modifier(entry.emitter, "FLOW")
    return modifier.show_viewport and modifier.show_render


def _problem(entry):
    return panel.entry_problem(entry) or ""


def test_a_renamed_group_stops_the_fire():
    entry = _entry()
    grid = _grid()
    entry.burn_from_choice = "Left"
    lib.check("a chosen group burns", _burning(entry) and _problem(entry) == "", _problem(entry))

    def rename(name):
        def change():
            grid.vertex_groups[grid.vertex_groups.find(name[0])].name = name[1]
            bpy.context.view_layer.update()
        return change
    clears = _counting_clears(rename(("Left", "Left Side")))
    lib.check("renaming it stops the flow, in the viewport and renders", not _burning(entry))
    lib.check("and it simulates again", clears >= 1, str(clears))
    lib.check("Burn From keeps the old name", entry.burn_from == "Left")
    lib.check("the box names the group and says what to do",
              '"Left"' in _problem(entry) and "Burn From" in _problem(entry) and "stopped" in _problem(entry),
              _problem(entry))
    items = [item[1] for item in sim_mesh_fire.burn_from_items(entry)]
    lib.check("the menu shows it as missing", entry.burn_from_choice == "Left" and items[-1] == "Left (missing)",
              str(items))
    left, right = _flame()
    lib.info(f"renamed: flame {left:.2f} left, {right:.2f} right")
    lib.check("no fire comes from anywhere", left + right < 0.01 * STATE["whole"], f"{left + right:.2f}")
    lib.check("the preset isn't marked modified", not sim_presets.is_modified(entry))

    clears = _counting_clears(rename(("Left Side", "Left")))
    lib.check("its old name back brings the flow back", _burning(entry) and _problem(entry) == "", _problem(entry))
    lib.check("and it simulates again", clears >= 1, str(clears))
    _burns_left_only("renamed back")


def test_a_deleted_group_stops_the_fire_until_another_is_chosen():
    entry = _entry()
    grid = _grid()
    grid.vertex_groups.remove(grid.vertex_groups["Left"])
    bpy.context.view_layer.update()
    lib.check("deleting the group stops the flow", not _burning(entry) and '"Left"' in _problem(entry),
              _problem(entry))
    lib.check("the emitter still mirrors the mesh", _synced(), str(_groups(entry.emitter)))
    entry.burn_from_choice = "Half"
    lib.check("choosing another brings it back", _burning(entry) and _problem(entry) == ""
              and sim_fire.flow_settings(entry).density_vertex_group == "Half", _problem(entry))
    copy = entry.emitter.evaluated_get(bpy.context.evaluated_depsgraph_get()).data
    lib.check("the copy's weights follow the mesh's new order", _weight_sums(copy) == _weight_sums(grid.data),
              f"{_weight_sums(copy)} / {_weight_sums(grid.data)}")
    left, right = _flame()
    lib.check("and it burns from that group", left > 1.0 and right > 0.02 * left, f"{left:.1f} / {right:.1f}")
    entry.burn_from_choice = sim_mesh_fire.WHOLE_MESH
    STATE["before"] = _weights(grid)


def test_refusals_are_plain():
    count = len(lib.scene().fas_effects)
    bpy.ops.object.empty_add()
    empty = bpy.context.object
    flat = bpy.data.objects.new("No Faces", bpy.data.meshes.new("No Faces"))
    flat.data.from_pydata([(0, 0, 0), (1, 0, 0)], [(0, 1)], [])
    lib.scene().collection.objects.link(flat)
    original = mesh_fire.MAX_FACES
    cases = (("a non-mesh", empty, "Select a mesh"), ("a mesh with no faces", flat, "no faces"),
             ("a mesh over the face limit", _grid(), "over the limit"))
    try:
        for what, obj, words in cases:
            if obj is _grid():
                mesh_fire.MAX_FACES = 100
            bpy.context.view_layer.objects.active = obj
            try:
                result = bpy.ops.fas.effect_create(preset=PRESET)
            except RuntimeError as exc:
                result = {"CANCELLED"}
                lib.check(f"refuses {what} plainly", words in str(exc), str(exc)[:120])
            lib.check(f"refuses {what}", result == {"CANCELLED"})
        lib.check("a fire on a mesh now over the limit says so", "over the face limit" in _problem(_entry()),
                  _problem(_entry()))
    finally:
        mesh_fire.MAX_FACES = original
    lib.check("nothing half-built is left", len(lib.scene().fas_effects) == count)
    bpy.data.objects.remove(empty)
    bpy.data.objects.remove(flat)
    bpy.context.view_layer.objects.active = _grid()


def test_a_deleted_mesh_stops_its_fire():
    bpy.ops.mesh.primitive_cube_add(size=0.5, location=(4.0, 0.0, 0.25))
    cube = bpy.context.object
    bpy.ops.fas.effect_create(preset=PRESET)
    entry = lib.scene().fas_effects[-1]
    uuid = entry.uuid
    lib.check("a second fire burns its own cube", entry.source == cube and _burning(entry))
    bpy.data.objects.remove(cube)
    bpy.context.view_layer.update()
    lib.check("with the cube deleted, its flow stops", entry.source is None and not _burning(entry))
    lib.check("the box says the mesh is gone and what to do",
              "mesh this fire was on is gone" in _problem(entry) and "Delete the fire" in _problem(entry),
              _problem(entry))
    lib.check("the panel still draws it", "can't be displayed" not in " ".join(_drawn()), " ".join(_drawn()))
    bpy.ops.fas.effect_delete(uuid=uuid)
    owned = [o.name for o in bpy.data.objects if o.get(lib.C.OWNER_PROP) and uuid in str(o.get(lib.C.OWNER_PROP))]
    lib.check("and Delete still cleans it up", not owned and not any(e.uuid == uuid for e in lib.scene().fas_effects),
              str(owned))
    lib.check("the first fire still burns", _burning(_entry()))
    bpy.context.view_layer.objects.active = _grid()


def _drawn():
    labels = []

    class StandIn:
        def __getattr__(self, _name):
            return None

        def __setattr__(self, name, value):
            object.__setattr__(self, name, value)

        def _child(self, *_args, **_kwargs):
            return StandIn()
        row = column = box = split = _child

        def label(self, text="", **_kwargs):
            labels.append(text)

        def prop(self, *_args, **_kwargs):
            pass

        def operator(self, *_args, **_kwargs):
            return type("Op", (), {})()
    from types import SimpleNamespace
    context = SimpleNamespace(scene=lib.scene(), active_object=None, space_data=None)
    panel.FAS_PT_effects.draw(SimpleNamespace(layout=StandIn()), context)
    return labels


def test_a_dense_mesh_warns_and_its_cost():
    bpy.ops.mesh.primitive_grid_add(x_subdivisions=710, y_subdivisions=710, size=2.0, location=(0.0, 4.0, 0.1))
    dense = bpy.context.object
    faces = len(dense.data.polygons)
    lib.check("the test mesh is over the warning", faces > mesh_fire.WARN_FACES, f"{faces:,}")
    lib.check("Create warns about it", "dense" in (sim_mesh_fire.dense_warning(dense) or ""))
    lib.check("but the grid isn't dense", sim_mesh_fire.dense_warning(_grid()) is None)
    result = bpy.ops.fas.effect_create(preset=PRESET)
    entry = lib.scene().fas_effects[-1]
    lib.check("and doesn't refuse it", result == {"FINISHED"} and entry.source == dense)
    scene = lib.scene()
    scene.frame_set(1)
    start = time.perf_counter()
    for frame in range(2, 12):
        scene.frame_set(frame)
    per_frame = (time.perf_counter() - start) / 10.0 * 1000.0
    lib.info(f"a {faces:,}-face 2 m grid at 64 divisions: {per_frame:.0f} ms a frame, headless, first play")
    lib.check("it simulates", per_frame > 0.0)
    scene.frame_set(1)
    bpy.ops.fas.effect_delete(uuid=entry.uuid)
    bpy.data.objects.remove(dense)
    bpy.context.view_layer.objects.active = _grid()


def test_delete_cleans_up():
    bpy.ops.fas.effect_delete(uuid=STATE["uuid"])
    owned = [o.name for o in bpy.data.objects if lib.C.OWNER_PROP in o.keys()]
    lib.check("nothing owned is left", not owned, str(owned))
    lib.check("the mesh keeps its groups", _weights(_grid()) == STATE["before"])


lib.main(globals())
