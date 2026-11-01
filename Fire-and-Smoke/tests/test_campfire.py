# SPDX-License-Identifier: GPL-3.0-or-later
"""The Campfire: builds cleanly, faces the camera, moves over time, never renders black."""

import os
import sys

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fas_testlib as lib  # noqa: E402

import bpy  # noqa: E402
from mathutils import Vector  # noqa: E402

STATE = {}


def _fire():
    return STATE["fire"]


def test_create():
    lib.add_camera()
    lib.setup_render()
    before = set(bpy.data.objects)
    result = bpy.ops.fas.campfire_create()
    lib.check("operator finishes", result == {"FINISHED"})
    new = set(bpy.data.objects) - before
    STATE["fire"] = next(o for o in new if o.type == "MESH")
    STATE["light"] = next(o for o in new if o.type == "LIGHT")
    bpy.context.view_layer.update()
    modifier = _fire().modifiers[0]
    lib.check("no node warnings", not list(modifier.node_warnings),
              str([w.message for w in modifier.node_warnings]))
    lib.check("planes exist", lib.instance_count(_fire()) == 28, str(lib.instance_count(_fire())))


def test_hidden_from_lighting():
    fire = _fire()
    lib.check("planes cast no shadow and aren't lit into the scene",
              not fire.visible_shadow and not fire.visible_diffuse and not fire.visible_glossy)


def test_faces_the_camera_as_it_moves():
    camera = lib.scene().camera
    facing = lib.first_instance_facing(_fire())
    lib.check("faces the camera", facing is not None and facing.dot(Vector((0, -1, 0))) > 0.99, str(facing))
    camera.location = (8.0, 0.0, 1.5)
    bpy.context.view_layer.update()
    facing = lib.first_instance_facing(_fire())
    lib.check("follows a moved camera", facing.dot(Vector((1, 0, 0))) > 0.99, str(facing))
    lib.check("spins around the vertical axis only", abs(facing.z) < 1e-5, str(facing))
    camera.location = (0.0, -8.0, 1.5)
    bpy.context.view_layer.update()


def test_bounce_limit_above_planes():
    limit = lib.scene().cycles.transparent_max_bounces
    lib.check("limit raised above the plane count", limit > 28, str(limit))


def test_time_reaches_the_material():
    lib.scene().frame_set(10)
    a = lib.render(lib.eevee_id())
    lib.scene().frame_set(24)
    b = lib.render(lib.eevee_id())
    lib.check("frames differ", lib.mean_diff(a, b) > 1e-4, f"{lib.mean_diff(a, b):.5f}")


def test_flicker_with_no_python():
    light = STATE["light"]
    values = set()
    for frame in (1, 6, 11, 16, 21):
        lib.scene().frame_set(frame)
        depsgraph = bpy.context.evaluated_depsgraph_get()
        values.add(round(light.evaluated_get(depsgraph).data.energy, 2))
    lib.check("light energy changes over frames", len(values) >= 4, str(values))
    lib.check("no handlers registered by the add-on",
              not [h for h in bpy.app.handlers.frame_change_post if "fas" in h.__name__])


def test_no_black_in_cycles():
    lib.scene().frame_set(24)
    pixels = lib.render("CYCLES")
    lib.check("no black pixels at the raised limit", lib.darkest(pixels) > 0.05, f"{lib.darkest(pixels):.4f}")
    lib.scene().cycles.transparent_max_bounces = 2
    pixels = lib.render("CYCLES")
    lib.check("the check does catch black at a low limit", lib.darkest(pixels) < 0.01,
              f"{lib.darkest(pixels):.4f}")
    lib.scene().cycles.transparent_max_bounces = 29


lib.main(globals())
