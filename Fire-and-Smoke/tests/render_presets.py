# SPDX-License-Identifier: GPL-3.0-or-later
"""One render per preset, per engine, for the eye checks and the release gate.

    blender -b --factory-startup --python tests/render_presets.py -- --out DIR [--size WxH]
        [--only SIMULATED_CAMPFIRE,EMBERS] [--frame 40]

Writes one PNG per preset and engine, and a contact sheet per engine.  Each preset gets
a camera fitted to its size, on dusk ground for fire and overcast ground for smoke.
"""

import math
import os
import sys

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fas_testlib as lib  # noqa: E402

import bpy  # noqa: E402
from fire_and_smoke.effects import presets  # noqa: E402
from mathutils import Vector  # noqa: E402

OUT = lib._arg("--out", os.path.join(lib.REPO, "look_test_output", "presets"))
WIDTH, HEIGHT = (int(v) for v in lib._arg("--size", "640x360").split("x"))
ONLY = [p for p in lib._arg("--only", "").split(",") if p]
FRAME = int(lib._arg("--frame", "40"))
VERSION = "%d.%d" % bpy.app.version[:2]
DUSK = (0.006, 0.009, 0.018, 1.0)
OVERCAST = (0.42, 0.5, 0.62, 1.0)

# preset -> (camera distance, look-at height, sky)
SHOTS = {
    "CANDLE": (0.7, 0.07, DUSK),
    "TORCH": (2.2, 0.3, DUSK),
    "CAMPFIRE": (8.0, 0.9, DUSK),
    "BONFIRE": (16.0, 2.0, DUSK),
    "BURNING_OBJECT": (11.0, 1.4, DUSK),
    "THIN_SMOKE": (13.0, 2.2, OVERCAST),
    "BLACK_SMOKE_COLUMN": (32.0, 6.0, OVERCAST),
    "EMBERS": (5.0, 1.6, DUSK),
    "SIMULATED_CAMPFIRE": (8.0, 0.9, DUSK),
}


def _scene_for(preset_id):
    distance, height, sky = SHOTS[preset_id]
    scene = bpy.context.scene
    for obj in list(scene.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    scene.render.resolution_x, scene.render.resolution_y = WIDTH, HEIGHT
    scene.render.image_settings.file_format = "PNG"
    scene.cycles.samples = 48
    scene.cycles.use_denoising = True
    scene.eevee.taa_render_samples = 16
    world = scene.world or bpy.data.worlds.new("Sky")
    scene.world = world
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs[0].default_value = sky

    bpy.ops.mesh.primitive_plane_add(size=max(distance * 8.0, 20.0))
    ground = bpy.context.object
    material = bpy.data.materials.new("Ground")
    material.use_nodes = True
    material.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.09, 0.075, 0.06, 1.0)
    ground.data.materials.append(material)

    camera = bpy.data.objects.new("Camera", bpy.data.cameras.new("Camera"))
    camera.data.lens = 50.0
    scene.collection.objects.link(camera)
    scene.camera = camera
    angle = math.radians(25.0)
    camera.location = (distance * math.sin(angle), -distance * math.cos(angle), height + distance * 0.08)
    camera.rotation_euler = (Vector((0.0, 0.0, height)) - camera.location).to_track_quat("-Z", "Y").to_euler()

    scene.frame_start, scene.frame_end = 1, max(60, FRAME)
    scene.frame_set(1)
    if preset_id == "BURNING_OBJECT":
        bpy.ops.mesh.primitive_cube_add(size=2.0, location=(0.0, 0.0, 1.0))
        crate = bpy.context.object
        crate.name = "Crate"
        crate.data.materials.append(material)
        bpy.context.view_layer.objects.active = crate
    bpy.ops.fas.effect_create(preset=preset_id)
    # Particles and the simulated fire need stepping from the start; flames don't mind.
    # Replay only simulates forward, so never jump: one frame at a time from frame 1.
    scene.frame_set(1)
    for frame in range(1, FRAME + 1):
        scene.frame_set(frame)
    return scene


def _contact_sheet(paths, target):
    images = [bpy.data.images.load(p) for p in paths]
    w, h = images[0].size
    columns = 4
    rows = math.ceil(len(images) / columns)
    sheet = bpy.data.images.new("sheet", w * columns, h * rows, alpha=False)
    pixels = [0.0] * (4 * w * columns * h * rows)
    for index, image in enumerate(images):
        source = list(image.pixels)
        col, row = index % columns, rows - 1 - index // columns
        for y in range(h):
            start = (row * h + y) * w * columns * 4 + col * w * 4
            pixels[start:start + w * 4] = source[y * w * 4:(y + 1) * w * 4]
    sheet.pixels = pixels
    sheet.filepath_raw = target
    sheet.file_format = "PNG"
    sheet.save()


def main():
    os.makedirs(OUT, exist_ok=True)
    made = {"CYCLES": [], "EEVEE": []}
    for preset_id in [p for p in presets.DISPLAY_ORDER if not ONLY or p in ONLY]:
        scene = _scene_for(preset_id)
        for name, engine in (("CYCLES", "CYCLES"), ("EEVEE", lib.eevee_id())):
            scene.render.engine = engine
            path = os.path.join(OUT, f"{VERSION}_{preset_id}_{name}.png")
            scene.render.filepath = path
            bpy.ops.render.render(write_still=True)
            made[name].append(path)
            print(f"PRESET {preset_id} {name} done", flush=True)
    for name, paths in made.items():
        _contact_sheet(paths, os.path.join(OUT, f"{VERSION}_sheet_{name}.png"))
    print("PRESET all done", flush=True)


main()
