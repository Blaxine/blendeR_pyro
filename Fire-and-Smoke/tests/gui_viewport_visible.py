# SPDX-License-Identifier: GPL-3.0-or-later
"""Every preset really draws in a viewport.  Needs a window, so it isn't part of the suite;
it opens Blender, screenshots the viewport with and without each preset, reports and quits.

    blender --factory-startup --python tests/gui_viewport_visible.py -- SOLID
    blender --factory-startup --python tests/gui_viewport_visible.py -- RENDERED

Final renders and particle counts can't catch this: embers once rendered correctly and
counted correctly while drawing nothing at all in the viewport.
"""

import math
import os
import sys
import tempfile

SHADING = sys.argv[sys.argv.index("--") + 1]
sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.argv = [sys.argv[0], "--"]
import fas_testlib as lib  # noqa: E402

import bpy  # noqa: E402
from fire_and_smoke.effects import presets  # noqa: E402
from mathutils import Quaternion  # noqa: E402

# preset -> viewing distance.  The view sits off to one side, clear of the first-run splash.
DISTANCES = {"CANDLE": 1.0, "TORCH": 2.5, "CAMPFIRE": 9.0, "BONFIRE": 18.0, "BURNING_OBJECT": 11.0,
             "THIN_SMOKE": 14.0, "BLACK_SMOKE_COLUMN": 34.0, "EMBERS": 9.0}
MIN_CHANGED = {"SOLID": 150, "RENDERED": 150}
SETTLE = 8.0 if SHADING == "RENDERED" else 1.5
OUT = tempfile.mkdtemp(prefix="fas_viewport_")

QUEUE = list(presets.DISPLAY_ORDER)
STATE = {"phase": "setup", "failed": 0}


def _viewport():
    window = bpy.context.window_manager.windows[0]
    area = max((a for a in window.screen.areas if a.type == "VIEW_3D"), key=lambda a: a.width * a.height)
    region = next(r for r in area.regions if r.type == "WINDOW")
    return window, area, region


def _shot(name):
    window, area, region = _viewport()
    path = os.path.join(OUT, f"{name}.png")
    with bpy.context.temp_override(window=window, area=area, region=region):
        bpy.ops.screen.screenshot_area(filepath=path)
    return path


def _changed(path_a, path_b):
    """Pixels that differ, in the part of the viewport left of the first-run splash."""
    a, b = bpy.data.images.load(path_a), bpy.data.images.load(path_b)
    w, h = a.size
    pa, pb = a.pixels[:], b.pixels[:]
    count = 0
    for y in range(h):
        for x in range(int(w * 0.42)):
            i = (y * w + x) * 4
            if abs(pa[i] - pb[i]) + abs(pa[i + 1] - pb[i + 1]) + abs(pa[i + 2] - pb[i + 2]) > 0.12:
                count += 1
    bpy.data.images.remove(a)
    bpy.data.images.remove(b)
    return count


def _aim(preset_id):
    _window, area, _region = _viewport()
    distance = DISTANCES[preset_id]
    view = area.spaces.active.region_3d
    view.view_perspective = "PERSP"
    view.view_distance = distance
    view.view_location = (distance * 0.36, 0.0, distance * 0.13)
    view.view_rotation = Quaternion((1.0, 0.0, 0.0), math.radians(85.0))
    area.tag_redraw()


def run():
    window, area, _region = _viewport()
    scene = window.scene
    phase = STATE["phase"]
    if phase == "setup":
        area.spaces.active.shading.type = SHADING
        bpy.data.objects["Cube"].hide_viewport = True
        STATE["phase"] = "aim"
        return 0.5
    if phase == "aim":
        if not QUEUE:
            print(f"VISIBLE done {bpy.app.version_string} {SHADING}: {STATE['failed']} failed", flush=True)
            bpy.ops.wm.quit_blender()
            return None
        scene.frame_set(1)
        _aim(QUEUE[0])
        burning = QUEUE[0] == "BURNING_OBJECT"
        bpy.data.objects["Cube"].hide_viewport = not burning
        if burning:
            window.view_layer.objects.active = bpy.data.objects["Cube"]
        STATE["phase"] = "before"
        return SETTLE
    if phase == "before":
        for frame in range(1, 61):
            scene.frame_set(frame)
        area.tag_redraw()
        STATE["phase"] = "baseline"
        return SETTLE
    if phase == "baseline":
        STATE["before"] = _shot(f"{QUEUE[0]}_before")
        scene.frame_set(1)
        with bpy.context.temp_override(window=window):
            bpy.ops.fas.effect_create(preset=QUEUE[0])
        for frame in range(1, 61):
            scene.frame_set(frame)
        area.tag_redraw()
        STATE["phase"] = "after"
        return SETTLE
    if phase == "after":
        changed = _changed(STATE["before"], _shot(f"{QUEUE[0]}_after"))
        ok = changed >= MIN_CHANGED[SHADING]
        STATE["failed"] += 0 if ok else 1
        print(f"VISIBLE {'PASS' if ok else 'FAIL'} {QUEUE[0]} {SHADING}: {changed} pixels changed", flush=True)
        with bpy.context.temp_override(window=window):
            bpy.ops.fas.effect_delete(uuid=scene.fas_effects[-1].uuid)
        QUEUE.pop(0)
        STATE["phase"] = "aim"
        return 0.5
    return None


bpy.app.timers.register(run, first_interval=2.0)
