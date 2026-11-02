# SPDX-License-Identifier: GPL-3.0-or-later
"""App handlers: copied effects get re-identified, and embers follow the timeline."""

import bpy
from bpy.app.handlers import persistent

from .. import constants as C
from . import copies, errors, naming

_scene_count = [0]
_ranges = {}          # scene name -> (frame_start, frame_end) last seen


def check_scenes():
    """Also run by the view sync timer: a new scene doesn't always cause a depsgraph update."""
    count = len(bpy.data.scenes)
    changed = count != _scene_count[0]
    _scene_count[0] = count
    if changed:
        try:
            copies.reidentify()
        except Exception as exc:
            errors.record("Fire and Smoke couldn't set up a copied scene", exc)
            errors.schedule()


def note_ranges():
    """Remember each scene's range, so the next change has something to compare."""
    _ranges.clear()
    for scene in bpy.data.scenes:
        _ranges[scene.name] = (float(scene.frame_start), float(scene.frame_end))


def _follow_range(scene, old):
    """Embers that ran for the whole old range run for the new one, at the same rate.
    A range the buyer set on the emitter is theirs."""
    start, end = scene.frame_start, scene.frame_end
    ratio = (end - start + 1) / max(old[1] - old[0] + 1, 1)
    for entry in scene.fas_effects:
        if entry.kind != C.KIND_EMBERS or entry.primary is None:
            continue
        for system in entry.primary.particle_systems:
            settings = system.settings
            if not naming.owned_by(settings, entry.uuid):
                continue
            if (settings.frame_start, settings.frame_end) != old:
                continue
            # Each bound is clamped by the other, so widen before narrowing.
            if start > settings.frame_end:
                settings.frame_end = end
                settings.frame_start = start
            else:
                settings.frame_start = start
                settings.frame_end = end
            settings.count = max(1, min(round(settings.count * ratio), C.MAX_EMBERS))
            entry.base_count = max(1, min(round(entry.base_count * ratio), C.MAX_EMBERS))


def follow_ranges():
    for scene in bpy.data.scenes:
        now = (float(scene.frame_start), float(scene.frame_end))
        old = _ranges.get(scene.name)
        _ranges[scene.name] = now
        if old is not None and old != now:
            try:
                _follow_range(scene, old)
            except Exception as exc:
                errors.record("Fire and Smoke couldn't follow the timeline", exc)
                errors.schedule()


@persistent
def fas_scene_watch(_scene, _depsgraph=None):
    check_scenes()
    follow_ranges()


@persistent
def fas_on_load(_dummy=None):
    _scene_count[0] = 0
    check_scenes()
    note_ranges()


def register():
    _scene_count[0] = len(bpy.data.scenes) if hasattr(bpy.data, "scenes") else 0
    _ranges.clear()
    if fas_scene_watch not in bpy.app.handlers.depsgraph_update_post:
        bpy.app.handlers.depsgraph_update_post.append(fas_scene_watch)
    if fas_on_load not in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.append(fas_on_load)


def unregister():
    if fas_scene_watch in bpy.app.handlers.depsgraph_update_post:
        bpy.app.handlers.depsgraph_update_post.remove(fas_scene_watch)
    if fas_on_load in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.remove(fas_on_load)
