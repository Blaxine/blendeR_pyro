# SPDX-License-Identifier: GPL-3.0-or-later
"""Facing rule and view sync: renders face the camera, the viewport follows the view target."""

import os
import sys

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fas_testlib as lib  # noqa: E402

import bpy  # noqa: E402
from fire_and_smoke.core import view_sync  # noqa: E402
from fire_and_smoke.effects import plane_stack  # noqa: E402
from mathutils import Vector  # noqa: E402

STATE = {}


def _modifier():
    return STATE["fire"].modifiers[0]


def _facing():
    bpy.context.view_layer.update()
    return lib.first_instance_facing(STATE["fire"])


def test_setup():
    lib.add_camera()
    lib.setup_render()
    before = set(bpy.data.objects)
    bpy.ops.fas.campfire_create()
    STATE["fire"] = next(o for o in set(bpy.data.objects) - before if o.type == "MESH")
    lib.check("no node warnings", not list(_modifier().node_warnings),
              str([w.message for w in _modifier().node_warnings]))
    lib.check("Face Viewport is on by default", bool(plane_stack.get_input(_modifier(), "Face Viewport")))
    lib.check("the scene has a view target", lib.scene().fas_view_target is not None)


def test_viewport_follows_the_target_only_with_the_switch_on():
    target = lib.scene().fas_view_target
    target.location = (8.0, 0.0, 1.5)
    facing = _facing()
    lib.check("switch on: faces the view target", facing.dot(Vector((1, 0, 0))) > 0.99, str(facing))
    plane_stack.set_inputs(_modifier(), {"Face Viewport": False})
    facing = _facing()
    lib.check("switch off: faces the camera", facing.dot(Vector((0, -1, 0))) > 0.99, str(facing))
    plane_stack.set_inputs(_modifier(), {"Face Viewport": True})


def test_render_ignores_the_view_target():
    lib.scene().frame_set(24)
    target = lib.scene().fas_view_target
    target.location = (8.0, 0.0, 1.5)
    bpy.context.view_layer.update()
    side_on = lib.render(lib.eevee_id())
    target.location = lib.scene().camera.location
    bpy.context.view_layer.update()
    at_camera = lib.render(lib.eevee_id())
    lib.check("render matches whatever the target does", lib.mean_diff(side_on, at_camera) < 1e-5,
              f"{lib.mean_diff(side_on, at_camera):.6f}")
    plane_stack.set_inputs(_modifier(), {"Face Viewport": False})
    bpy.context.view_layer.update()
    switched = lib.render(lib.eevee_id())
    lib.check("render matches whatever the switch says", lib.mean_diff(switched, at_camera) < 1e-5,
              f"{lib.mean_diff(switched, at_camera):.6f}")
    plane_stack.set_inputs(_modifier(), {"Face Viewport": True})


def test_most_recently_moved_viewport_wins():
    view_sync.reset()
    a, b = Vector((1, 0, 0)), Vector((0, 1, 0))
    view_sync.note_views([("left", 1, a), ("right", 1, b)])
    view_sync.note_views([("left", 1, Vector((5, 0, 0))), ("right", 1, b)])
    lib.check("the moved viewport wins", view_sync.latest(1) == Vector((5, 0, 0)))
    view_sync.note_views([("left", 1, Vector((5, 0, 0))), ("right", 1, Vector((0, 7, 0)))])
    lib.check("then the other one", view_sync.latest(1) == Vector((0, 7, 0)))
    view_sync.note_views([("left", 1, Vector((5, 0, 0))), ("right", 1, Vector((0, 7, 0)))])
    lib.check("no movement changes nothing", view_sync.latest(1) == Vector((0, 7, 0)))
    view_sync.note_views([("other", 2, Vector((9, 9, 9)))])
    lib.check("scenes stay separate", view_sync.latest(1) == Vector((0, 7, 0)))
    view_sync.reset()


def test_writes_only_on_movement():
    scene = lib.scene()
    target = scene.fas_view_target
    lib.check("a new position writes", view_sync.write_position(scene, Vector((3, 3, 3))))
    lib.check("the target moved", (target.location - Vector((3, 3, 3))).length < 1e-6)
    lib.check("the same position doesn't", not view_sync.write_position(scene, Vector((3, 3, 3))))


def test_tick_runs_headless():
    lib.check("the timer keeps running with no windows", view_sync.tick() is not None)


def test_steep_views_fade():
    camera = lib.scene().camera
    lights = [o for o in lib.scene().objects if o.type == "LIGHT"]
    for light in lights:
        light.hide_render = True
    lib.scene().frame_set(24)
    side = lib.render(lib.eevee_id())
    camera.location = (0.0, -0.3, 12.0)
    camera.rotation_euler = (0.02, 0.0, 0.0)
    bpy.context.view_layer.update()
    top = lib.render(lib.eevee_id())
    camera.location = (0.0, -8.0, 1.5)
    bpy.context.view_layer.update()
    for light in lights:
        light.hide_render = False

    def peak(pixels, channel):
        return max(pixels[i + channel] for i in range(0, len(pixels), 4))

    lib.check("a glow remains from straight above", peak(top, 0) > 0.3, f"{peak(top, 0):.3f}")
    lib.check("the bright flame core is gone from straight above", peak(top, 1) < peak(side, 1),
              f"{peak(top, 1):.3f} / {peak(side, 1):.3f}")


def test_no_camera():
    scene = lib.scene()
    camera = scene.camera
    scene.camera = None
    bpy.context.view_layer.update()
    plane_stack.set_inputs(_modifier(), {"Face Viewport": False})
    facing = _facing()
    lib.check("with no camera the planes still evaluate", facing is not None, str(facing))
    lib.check("no node warnings with no camera", not list(_modifier().node_warnings))
    plane_stack.set_inputs(_modifier(), {"Face Viewport": True})
    scene.camera = camera


def test_unregister_stops_the_timer():
    lib.check("timer registered", view_sync.is_running())
    lib.addon.unregister()
    lib.check("timer gone after unregister", not view_sync.is_running())
    lib.check("load handler gone", view_sync._on_load not in bpy.app.handlers.load_post)
    lib.addon.register()


lib.main(globals())
