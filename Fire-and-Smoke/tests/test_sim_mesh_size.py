# SPDX-License-Identifier: GPL-3.0-or-later
"""Fire and Smoke from Mesh at any size, and on a moving mesh.

The presets are corrected for the mesh's size, measured once at Create: a 0.5, 2 and
8 m cube each burn with flames one to two cube-heights above their top.  A mesh that
moves carries its fire.  Every check that plays steps one frame at a time from the
first frame, since Replay only simulates forward.
"""

import os
import sys

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fas_testlib as lib  # noqa: E402

import bpy  # noqa: E402
from fire_and_smoke.effects import fire_light, sim_fire, sim_mesh_fire, sim_presets  # noqa: E402

PRESET = "SIMULATED_MESH_FIRE"
# Flame this strong is what a render shows; fainter flame barely glows.
VISIBLE = 0.3
SAMPLES = (40, 45, 50, 55, 60)
STATE = {}


def _evaluated(entry):
    depsgraph = bpy.context.evaluated_depsgraph_get()
    return sim_fire.find_modifier(entry.primary.evaluated_get(depsgraph), "DOMAIN").domain_settings


def _flame_top_above(entry, source):
    """How far the visible flame reaches above the mesh's top, in mesh heights."""
    settings = _evaluated(entry)
    rx, ry, rz = settings.domain_resolution
    layer = rx * ry
    top = -1
    for index, value in enumerate(settings.flame_grid):
        if value > VISIBLE:
            top = max(top, index // layer)
    low, high = sim_mesh_fire.world_bounds(entry.primary)
    mesh_low, mesh_high = sim_mesh_fire.world_bounds(source)
    reach = low.z + (top + 1) * (high.z - low.z) / rz
    return (reach - mesh_high.z) / (mesh_high.z - mesh_low.z)


def _flame_centre_x(entry):
    settings = _evaluated(entry)
    rx = settings.domain_resolution[0]
    low, high = sim_mesh_fire.world_bounds(entry.primary)
    dx = (high.x - low.x) / rx
    total = weighted = 0.0
    for index, value in enumerate(settings.flame_grid):
        total += value
        weighted += value * (low.x + (index % rx + 0.5) * dx)
    return weighted / total if total > 0.0 else float("nan")


def _cube(size, location):
    bpy.ops.mesh.primitive_cube_add(size=size, location=location)
    cube = bpy.context.object
    cube.select_set(True)
    bpy.context.view_layer.objects.active = cube
    return cube


def _burn(size):
    lib.clear_scene()
    scene = lib.scene()
    scene.frame_start, scene.frame_end = 1, 60
    scene.frame_set(1)
    cube = _cube(size, (0.0, 0.0, size / 2.0))
    bpy.ops.fas.effect_create(preset=PRESET)
    return scene.fas_effects[-1], cube


def test_sizes_burn_alike():
    tall = {}
    for size in (0.5, 2.0, 8.0):
        entry, cube = _burn(size)
        scene = lib.scene()
        heights = []
        for frame in range(1, max(SAMPLES) + 1):
            scene.frame_set(frame)
            if frame in SAMPLES:
                heights.append(_flame_top_above(entry, cube))
        mean = sum(heights) / len(heights)
        settings = sim_fire.domain_settings(entry)
        lib.info(f"{size} m cube: flames {mean:.2f} cube-heights above its top over frames 40 to 60 "
                 f"({', '.join(f'{h:.2f}' for h in heights)}); burn {settings.burning_rate:.2f}, "
                 f"time {settings.time_scale:.2f}, light {fire_light.get_energy(entry.light.data):.0f} W")
        lib.check(f"a {size} m cube's flames rise one to two cube-heights above it", 1.0 <= mean <= 2.0,
                  f"{mean:.2f}")
        lib.check(f"its size was measured at Create", abs(entry.mesh_size - size) < 1e-4, f"{entry.mesh_size:.3f}")
        lib.check(f"and the preset isn't marked modified", not sim_presets.is_modified(entry))
        tall[size] = (settings.time_scale, settings.burning_rate, fire_light.get_energy(entry.light.data),
                      entry.light.data.shadow_soft_size, entry.base_density)
        scene.frame_set(1)
        bpy.ops.fas.effect_delete(uuid=entry.uuid)
    small, big = tall[0.5], tall[8.0]
    lib.check("time runs faster for a bigger fire", big[0] > tall[2.0][0] > small[0])
    lib.check("and it burns slower", big[1] < tall[2.0][1] < small[1])
    lib.check("its light is stronger, by its area", abs(big[2] / small[2] - 256.0) < 1.0, f"{big[2] / small[2]:.1f}")
    lib.check("and softer, by its size", abs(big[3] / small[3] - 16.0) < 0.01, f"{big[3] / small[3]:.2f}")
    lib.check("and its smoke is thinner per metre", abs(small[4] / big[4] - 16.0) < 0.01, f"{small[4] / big[4]:.2f}")


def test_apply_keeps_the_size_from_create():
    entry, cube = _burn(2.0)
    settings = sim_fire.domain_settings(entry)
    burn, time_scale = settings.burning_rate, settings.time_scale
    cube.scale = (3.0, 3.0, 3.0)
    bpy.context.view_layer.update()
    for preset in (sim_presets.NORMAL_FIRE, sim_presets.CAMPFIRE):
        entry.sim_preset_choice = preset
        bpy.ops.fas.apply_sim_preset(uuid=entry.uuid)
    lib.check("Apply corrects for the size measured at Create", abs(entry.mesh_size - 2.0) < 1e-4
              and abs(settings.burning_rate - burn) < 1e-4 and abs(settings.time_scale - time_scale) < 1e-4,
              f"{entry.mesh_size:.2f}, burn {settings.burning_rate:.3f} / {burn:.3f}")
    entry.mesh_size = 0.0
    bpy.ops.fas.apply_sim_preset(uuid=entry.uuid)
    lib.check("a fire saved before the size was kept measures its mesh at the next Apply",
              abs(entry.mesh_size - 6.0) < 1e-3 and settings.burning_rate < burn, f"{entry.mesh_size:.2f}")
    lib.check("the catalogue is never changed", sim_presets.CATALOG[sim_presets.CAMPFIRE]["domain"]["burning_rate"]
              == 0.9 and "time_scale" not in sim_presets.CATALOG[sim_presets.CAMPFIRE]["domain"])
    bpy.ops.fas.effect_delete(uuid=entry.uuid)


def test_a_moving_mesh_carries_its_fire():
    lib.clear_scene()
    scene = lib.scene()
    scene.frame_start, scene.frame_end = 1, 60
    scene.frame_set(1)
    cube = _cube(1.0, (0.0, 0.0, 0.5))
    cube.keyframe_insert("location", frame=1)
    cube.location.x = 1.5
    cube.keyframe_insert("location", frame=30)
    scene.frame_set(1)
    bpy.ops.fas.effect_create(preset=PRESET)
    entry = scene.fas_effects[-1]
    for frame in range(1, 31):
        scene.frame_set(frame)
    centre = _flame_centre_x(entry)
    lib.info(f"a 1 m cube moved 1.5 m over 30 frames: flame centre at x = {centre:.3f}, "
             f"the cube at {cube.matrix_world.translation.x:.3f}")
    lib.check("the flame ends within a tenth of the cube's width of it",
              abs(centre - cube.matrix_world.translation.x) <= 0.1, f"{centre:.3f}")
    scene.frame_set(1)
    bpy.ops.fas.effect_delete(uuid=entry.uuid)
    bpy.data.objects.remove(cube)


lib.main(globals())
