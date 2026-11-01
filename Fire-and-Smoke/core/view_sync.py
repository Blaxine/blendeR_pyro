# SPDX-License-Identifier: GPL-3.0-or-later
"""View sync: feeds the viewport's position to Geometry Nodes.

Geometry Nodes can't read the viewport from a modifier, so a timer finds the 3D
viewport whose view changed most recently and writes its position to the scene's
view target, an empty the plane stacks read.  Preview only: final renders ignore it.
"""

import bpy
from bpy.app.handlers import persistent
from mathutils import Vector

from .. import constants as C

ACTIVE_INTERVAL = 1.0 / 30.0
IDLE_INTERVAL = 0.5
MOVE_EPSILON = 0.001
TARGET_NAME = "FAS_ViewTarget"

_last = {}          # viewport key -> position last seen
_latest = {}        # scene pointer -> position of the most recently moved viewport
_error_logged = [False]


def reset():
    _last.clear()
    _latest.clear()


def note_views(views):
    """Record ``(viewport_key, scene_key, position)`` tuples; a moved view wins its scene."""
    for key, scene_key, position in views:
        old = _last.get(key)
        if old is None or (old - position).length > MOVE_EPSILON:
            _last[key] = position.copy()
            _latest[scene_key] = position.copy()


def latest(scene_key):
    return _latest.get(scene_key)


def write_position(scene, position):
    """Move the scene's view target; True when it changed."""
    target = scene.fas_view_target
    if target is None or (target.location - position).length <= MOVE_EPSILON:
        return False
    target.location = position
    return True


def default_position(scene):
    """Where a new view target starts: on the camera, or looking down -Y."""
    if scene.camera is not None:
        return scene.camera.matrix_world.translation.copy()
    return Vector((0.0, -10.0, 2.0))


def ensure_target(scene):
    """The scene's view target, created when missing."""
    target = scene.fas_view_target
    if target is not None and scene.objects.get(target.name) == target:
        return target
    target = bpy.data.objects.new(TARGET_NAME, None)
    target.empty_display_size = 0.01
    target.hide_select = True
    target.hide_render = True
    target.hide_viewport = True
    target.location = _latest.get(scene.as_pointer(), default_position(scene))
    scene.collection.objects.link(target)
    scene.fas_view_target = target
    return target


def _views(window):
    """Every 3D view in a window, including quad views."""
    for area in window.screen.areas:
        if area.type != "VIEW_3D":
            continue
        space = area.spaces.active
        regions = list(space.region_quadviews) or [space.region_3d]
        for index, region in enumerate(regions):
            if region is not None:
                yield (area.as_pointer(), index), area, region


def _rendering():
    try:
        return bpy.app.is_job_running("RENDER")
    except Exception:
        return False


def tick():
    """The timer: returns seconds until the next run."""
    try:
        wm = bpy.context.window_manager
        windows = list(getattr(wm, "windows", ()))
        if _rendering() or not any(s.fas_view_target for s in bpy.data.scenes):
            return IDLE_INTERVAL
        for window in windows:
            scene = window.scene
            views = [(key, scene.as_pointer(), region.view_matrix.inverted().translation)
                     for key, _area, region in _views(window)]
            note_views(views)
            position = latest(scene.as_pointer())
            if position is not None and write_position(scene, position):
                for _key, area, _region in _views(window):
                    area.tag_redraw()
    except Exception as exc:
        if not _error_logged[0]:
            _error_logged[0] = True
            print(f"[{C.DISPLAY_NAME}] view sync: {exc}")
    return ACTIVE_INTERVAL


@persistent
def _on_load(_dummy=None):
    reset()


def is_running():
    return bpy.app.timers.is_registered(tick)


def register():
    reset()
    if _on_load not in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.append(_on_load)
    if not is_running():
        bpy.app.timers.register(tick, first_interval=IDLE_INTERVAL, persistent=True)


def unregister():
    if is_running():
        bpy.app.timers.unregister(tick)
    if _on_load in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.remove(_on_load)
    reset()
