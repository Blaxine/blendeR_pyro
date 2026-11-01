# SPDX-License-Identifier: GPL-3.0-or-later
"""The look test: a fixed scene with a mid-ground orbiting camera, rendered in both engines.

    blender -b --factory-startup --python tests/look_test.py -- --out DIR [options]

      --stills            one contact sheet per engine instead of clips
      --preset NAME       what to create (default CAMPFIRE)
      --engines A,B       CYCLES, EEVEE or both (default both)
      --frames N          clip length (default 96)
      --size WxH          resolution (default 960x540)
      --speed             measure Cycles against an empty 1080p frame and print it

The scene is built here so it stays the same on every Blender version and between
rounds.  Colour management stays at factory settings, as a beginner's would.
"""

import math
import os
import sys
import time

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fas_testlib as lib  # noqa: E402

import bpy  # noqa: E402

OUT = lib._arg("--out", os.path.join(lib.REPO, "look_test_output"))
PRESET = lib._arg("--preset", "CAMPFIRE")
ENGINES = lib._arg("--engines", "CYCLES,EEVEE").split(",")
FRAMES = int(lib._arg("--frames", "96"))
WIDTH, HEIGHT = (int(v) for v in lib._arg("--size", "960x540").split("x"))
STILL_FRAMES = (12, 24, 36, 48, 60, 72)
VERSION = "%d.%d" % bpy.app.version[:2]


def _set_engine(name):
    bpy.context.scene.render.engine = "CYCLES" if name == "CYCLES" else lib.eevee_id()


def build_scene():
    scene = bpy.context.scene
    for obj in list(scene.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    scene.frame_start, scene.frame_end = 1, FRAMES
    scene.render.fps = 24
    scene.render.resolution_x, scene.render.resolution_y = WIDTH, HEIGHT
    scene.cycles.samples = 64
    scene.cycles.use_denoising = True
    scene.eevee.taa_render_samples = 32

    world = bpy.data.worlds.new("Dusk")
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs[0].default_value = (0.006, 0.009, 0.018, 1.0)
    scene.world = world

    bpy.ops.mesh.primitive_plane_add(size=60.0)
    ground = bpy.context.object
    ground.name = "Ground"
    material = bpy.data.materials.new("Ground")
    material.use_nodes = True
    bsdf = material.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = (0.09, 0.075, 0.06, 1.0)
    bsdf.inputs["Roughness"].default_value = 0.9
    ground.data.materials.append(material)

    # Mid-ground: the fire fills about a third of the frame height.
    pivot = bpy.data.objects.new("CameraPivot", None)
    scene.collection.objects.link(pivot)
    pivot.location = (0.0, 0.0, 0.9)
    camera = bpy.data.objects.new("Camera", bpy.data.cameras.new("Camera"))
    camera.data.lens = 50.0
    scene.collection.objects.link(camera)
    scene.camera = camera
    camera.parent = pivot
    camera.location = (0.0, -9.0, 0.7)
    camera.rotation_euler = (math.radians(90.0 - math.degrees(math.atan2(0.7, 9.0))), 0.0, 0.0)
    pivot.rotation_euler = (0.0, 0.0, 0.0)
    pivot.keyframe_insert("rotation_euler", index=2, frame=1)
    pivot.rotation_euler = (0.0, 0.0, math.radians(70.0))
    pivot.keyframe_insert("rotation_euler", index=2, frame=FRAMES)
    scene.frame_set(1)
    return scene


def create_effect():
    if "campfire_create" in dir(bpy.ops.fas) and PRESET == "CAMPFIRE":
        return bpy.ops.fas.campfire_create()
    return bpy.ops.fas.effect_create(preset=PRESET)


def contact_sheet(paths, target):
    images = [bpy.data.images.load(p) for p in paths]
    w, h = images[0].size
    columns = 3
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


def render_stills(scene, engine):
    _set_engine(engine)
    paths = []
    for frame in STILL_FRAMES:
        scene.frame_set(frame)
        path = os.path.join(OUT, f"{VERSION}_{PRESET}_{engine}_f{frame:03d}.png")
        scene.render.filepath = path
        scene.render.image_settings.file_format = "PNG"
        bpy.ops.render.render(write_still=True)
        paths.append(path)
    contact_sheet(paths, os.path.join(OUT, f"{VERSION}_{PRESET}_{engine}_sheet.png"))
    for path in paths:
        os.remove(path)


def render_clip(scene, engine):
    _set_engine(engine)
    render = scene.render
    if hasattr(render.image_settings, "media_type"):  # Blender 5.0+
        render.image_settings.media_type = "VIDEO"
    render.image_settings.file_format = "FFMPEG"
    render.ffmpeg.format = "MPEG4"
    render.ffmpeg.codec = "H264"
    render.filepath = os.path.join(OUT, f"{VERSION}_{PRESET}_{engine}_")
    start = time.perf_counter()
    bpy.ops.render.render(animation=True)
    print(f"LOOK clip {engine}: {time.perf_counter() - start:.1f} s for {FRAMES} frames", flush=True)


def measure_speed(scene):
    """Cycles against an empty frame at 1080p, on this PC."""
    _set_engine("CYCLES")
    scene.render.resolution_x, scene.render.resolution_y = 1920, 1080
    scene.render.image_settings.file_format = "PNG"
    scene.render.filepath = os.path.join(OUT, "speed.png")
    scene.frame_set(24)

    def timed():
        start = time.perf_counter()
        bpy.ops.render.render(write_still=True)
        return time.perf_counter() - start

    timed()  # the first render builds kernels: discard it
    empty = timed()
    create_effect()
    bpy.context.view_layer.update()
    timed()
    with_fire = timed()
    print(f"LOOK speed: empty {empty:.2f} s, with effect {with_fire:.2f} s, "
          f"{with_fire / empty:.2f}x", flush=True)
    os.remove(scene.render.filepath)


def main():
    os.makedirs(OUT, exist_ok=True)
    scene = build_scene()
    if "--speed" in lib.ARGS:
        measure_speed(scene)
        return
    create_effect()
    for engine in ENGINES:
        if "--stills" in lib.ARGS:
            render_stills(scene, engine)
        else:
            render_clip(scene, engine)
    print("LOOK done", flush=True)


main()
