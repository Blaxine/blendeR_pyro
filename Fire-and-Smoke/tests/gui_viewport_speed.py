# SPDX-License-Identifier: GPL-3.0-or-later
"""EEVEE viewport frame rate of the default Campfire.  Needs a window, so it isn't
part of the suite; it opens Blender, measures for a few seconds and quits.

    blender --factory-startup --python tests/gui_viewport_speed.py
"""

import os
import sys
import time

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fas_testlib as lib  # noqa: E402

import bpy  # noqa: E402


def _viewport():
    window = bpy.context.window_manager.windows[0]
    area = max((a for a in window.screen.areas if a.type == "VIEW_3D"),
               key=lambda a: a.width * a.height)
    region = next(r for r in area.regions if r.type == "WINDOW")
    return window, area, region


def measure():
    scene = bpy.context.scene
    window, area, region = _viewport()
    scene.render.engine = lib.eevee_id()
    area.spaces[0].shading.type = "RENDERED"
    area.spaces[0].region_3d.view_perspective = "CAMERA"
    scene.frame_start, scene.frame_end = 1, 48
    lib.add_camera(location=(0.0, -9.0, 1.6), look_at=(0.0, 0.0, 0.9))
    with bpy.context.temp_override(window=window, area=area, region=region):
        # Shaders compile on the first pass: discard it.
        bpy.ops.wm.redraw_timer(type="ANIM_STEP", iterations=1)
        bpy.ops.fas.campfire_create()
        bpy.ops.wm.redraw_timer(type="DRAW_WIN_SWAP", iterations=30)
        scene.frame_set(1)
        start = time.perf_counter()
        bpy.ops.wm.redraw_timer(type="ANIM_STEP", iterations=1)
        step = time.perf_counter() - start
        start = time.perf_counter()
        frames = 48
        for frame in range(1, frames + 1):
            scene.frame_set(frame)
            bpy.ops.wm.redraw_timer(type="DRAW_WIN_SWAP", iterations=1)
        elapsed = time.perf_counter() - start
    print(f"LOOK viewport {bpy.app.version_string}: {frames / elapsed:.1f} fps "
          f"({area.width}x{area.height}), one anim step {step:.2f} s", flush=True)
    bpy.ops.wm.quit_blender()


bpy.app.timers.register(measure, first_interval=2.0)
