# SPDX-License-Identifier: GPL-3.0-or-later
"""View sync in a real window.  Needs a window, so it isn't part of the suite; it
opens Blender, orbits two viewports from code, reports and quits.

    blender --factory-startup --python tests/gui_view_sync.py
"""

import math
import os
import sys

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fas_testlib as lib  # noqa: E402

import bpy  # noqa: E402
from mathutils import Quaternion, Vector  # noqa: E402

FIRE = {}
STEPS = []
FAILED = []


def report(name, ok, detail=""):
    if not ok:
        FAILED.append(name)
    print(f"GUI {'PASS' if ok else 'FAIL'} {name} {detail}", flush=True)


def _areas():
    window = bpy.context.window_manager.windows[0]
    return window, [a for a in window.screen.areas if a.type == "VIEW_3D"]


def _orbit(area, degrees):
    # A level view from azimuth ``degrees``; view_matrix only updates on the next redraw.
    region = area.spaces.active.region_3d
    region.view_perspective = "PERSP"
    region.view_location = (0.0, 0.0, 0.5)
    region.view_distance = 8.0
    angle = math.radians(degrees)
    region.view_rotation = Quaternion((0.0, 0.0, 1.0), angle) @ Quaternion((1.0, 0.0, 0.0), math.pi / 2)
    area.tag_redraw()
    return Vector((math.sin(angle), -math.cos(angle), 0.0))


def _facing_matches(expected):
    bpy.context.view_layer.update()
    facing = lib.first_instance_facing(FIRE["obj"])
    flat = Vector((expected.x, expected.y, 0.0)).normalized()
    return facing is not None and facing.dot(flat) > 0.98, f"facing {facing} expected {flat}"


def step_setup():
    window, areas = _areas()
    lib.add_camera()
    before = set(bpy.data.objects)
    bpy.ops.fas.campfire_create()
    FIRE["obj"] = next(o for o in set(bpy.data.objects) - before if o.type == "MESH")
    area = areas[0]
    region = next(r for r in area.regions if r.type == "WINDOW")
    with bpy.context.temp_override(window=window, area=area, region=region):
        bpy.ops.screen.area_split(direction="VERTICAL", factor=0.5)
    _, areas = _areas()
    report("two viewports exist", len(areas) == 2, str(len(areas)))


def step_orbit_first():
    _, areas = _areas()
    FIRE["expected"] = _orbit(areas[0], 40.0)


def step_check_first():
    ok, detail = _facing_matches(FIRE["expected"])
    report("planes follow the first viewport", ok, detail)
    _, areas = _areas()
    FIRE["expected"] = _orbit(areas[1], 200.0)


def step_check_second():
    ok, detail = _facing_matches(FIRE["expected"])
    report("planes follow the viewport that moved last", ok, detail)
    _, areas = _areas()
    FIRE["expected"] = _orbit(areas[0], 300.0)


def step_check_back():
    ok, detail = _facing_matches(FIRE["expected"])
    report("and back to the first when it moves", ok, detail)
    bpy.ops.ed.undo_push(message="test")


def step_undo_keeps_tracking():
    # Undo can restore the target's old position; the next tick must put it back.
    lib.scene().fas_view_target.location = (99.0, 99.0, 99.0)


def step_check_undo():
    target = lib.scene().fas_view_target
    report("a target moved by anything else returns to the view", (target.location - Vector((99, 99, 99))).length > 1)


def step_copy_scene():
    window = bpy.context.window_manager.windows[0]
    FIRE["source"] = window.scene
    with bpy.context.temp_override(window=window):
        bpy.ops.scene.new(type="FULL_COPY")


def step_check_copy():
    copied, source = bpy.context.window_manager.windows[0].scene, FIRE["source"]
    report("a copied scene was re-identified with no button pressed", copied != source
           and copied.fas_effects[0].uuid != source.fas_effects[0].uuid,
           f"{copied.name} {source.name} {[e.uuid[:8] for e in copied.fas_effects]} {[e.uuid[:8] for e in source.fas_effects]}")
    report("the copy has its own node tree",
           copied.fas_effects[0].primary.modifiers[0].node_group
           != source.fas_effects[0].primary.modifiers[0].node_group)


def step_finish():
    report("no errors from the timer", not __import__("fire_and_smoke.core.view_sync", fromlist=["x"])._error_logged[0])
    print(f"GUI done {bpy.app.version_string}: {len(FAILED)} failed", flush=True)
    bpy.ops.wm.quit_blender()


STEPS[:] = [step_setup, step_orbit_first, step_check_first, step_check_second, step_check_back,
            step_undo_keeps_tracking, step_check_undo, step_copy_scene, step_check_copy, step_finish]


def run():
    if not STEPS:
        return None
    step = STEPS.pop(0)
    try:
        step()
    except Exception as exc:
        import traceback
        traceback.print_exc()
        report(step.__name__, False, str(exc))
    return 0.6


bpy.app.timers.register(run, first_interval=2.0)
