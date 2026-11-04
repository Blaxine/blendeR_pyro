# SPDX-License-Identifier: GPL-3.0-or-later
"""EEVEE viewport frame rate of a default preset.  Needs a window, so it isn't part of
the suite; it opens Blender, measures for a few seconds and quits.

    blender --factory-startup --python tests/gui_viewport_speed.py
    blender --factory-startup --python tests/gui_viewport_speed.py -- SIMULATED_CAMPFIRE
    blender --factory-startup --python tests/gui_viewport_speed.py -- SIMULATED_CAMPFIRE 96
    blender --factory-startup --python tests/gui_viewport_speed.py -- SIMULATED_CAMPFIRE CANDLE_FIRE

The Campfire is timed playing frames it can show at once.  The Simulated Fire is timed
on its first play-through from frame 1, which simulates every frame, then on a second
pass that reads the cache.  It takes a Detail and a simulation preset, in any order.
"""

import os
import sys
import time

_AFTER = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
PRESET = _AFTER[0] if _AFTER else "CAMPFIRE"
# Simulated Fire only: a number is a Detail, a name a simulation preset.
DETAIL = next((int(a) for a in _AFTER[1:] if a.isdigit()), None)
SIM_PRESET = next((a for a in _AFTER[1:] if not a.isdigit()), "CAMPFIRE")
sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.argv = [sys.argv[0], "--"]
import fas_testlib as lib  # noqa: E402

import bpy  # noqa: E402

SIM_FRAMES = 96


def _viewport():
    window = bpy.context.window_manager.windows[0]
    area = max((a for a in window.screen.areas if a.type == "VIEW_3D"),
               key=lambda a: a.width * a.height)
    region = next(r for r in area.regions if r.type == "WINDOW")
    return window, area, region


def _play(scene, frames):
    start = time.perf_counter()
    for frame in range(1, frames + 1):
        scene.frame_set(frame)
        bpy.ops.wm.redraw_timer(type="DRAW_WIN_SWAP", iterations=1)
    return frames / (time.perf_counter() - start)


def measure_campfire(scene, area):
    scene.frame_start, scene.frame_end = 1, 48
    bpy.ops.fas.campfire_create()
    bpy.ops.wm.redraw_timer(type="DRAW_WIN_SWAP", iterations=30)
    scene.frame_set(1)
    start = time.perf_counter()
    bpy.ops.wm.redraw_timer(type="ANIM_STEP", iterations=1)
    step = time.perf_counter() - start
    fps = _play(scene, 48)
    print(f"LOOK viewport {bpy.app.version_string}: {fps:.1f} fps "
          f"({area.width}x{area.height}), one anim step {step:.2f} s", flush=True)


def measure_simulated(scene, area):
    scene.frame_start, scene.frame_end = 1, 250
    scene.frame_set(1)
    bpy.ops.fas.effect_create(preset="SIMULATED_CAMPFIRE", sim_preset=SIM_PRESET)
    entry = scene.fas_effects[-1]
    if DETAIL:
        entry.detail = DETAIL
    bpy.ops.wm.redraw_timer(type="DRAW_WIN_SWAP", iterations=10)
    scene.frame_set(1)
    first = _play(scene, SIM_FRAMES)
    scene.frame_set(1)
    cached = _play(scene, SIM_FRAMES)
    print(f"LOOK simulated {SIM_PRESET} {bpy.app.version_string}: first play-through {first:.1f} fps, "
          f"from the cache {cached:.1f} fps, frames 1 to {SIM_FRAMES} at {entry.detail} divisions "
          f"({area.width}x{area.height})", flush=True)


def measure():
    scene = bpy.context.scene
    window, area, region = _viewport()
    scene.render.engine = lib.eevee_id()
    area.spaces[0].shading.type = "RENDERED"
    area.spaces[0].region_3d.view_perspective = "CAMERA"
    lib.add_camera(location=(0.0, -9.0, 1.6), look_at=(0.0, 0.0, 0.9))
    with bpy.context.temp_override(window=window, area=area, region=region):
        # Shaders compile on the first pass: discard it.
        bpy.ops.wm.redraw_timer(type="ANIM_STEP", iterations=1)
        if PRESET == "SIMULATED_CAMPFIRE":
            measure_simulated(scene, area)
        else:
            measure_campfire(scene, area)
    bpy.ops.wm.quit_blender()


bpy.app.timers.register(measure, first_interval=2.0)
