# SPDX-License-Identifier: GPL-3.0-or-later
"""App handlers: copied effects get re-identified, embers and simulated fires follow the
timeline, and simulated fires keep their cache beside the saved .blend."""

import bpy
from bpy.app.handlers import persistent

from .. import constants as C
from . import cache_folder, copies, errors, naming

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


def _repoint(what, saved=False):
    try:
        cache_folder.repoint_all(saved)
    except Exception as exc:
        errors.record(f"Fire and Smoke couldn't point a simulation at its cache folder {what}", exc)
        errors.schedule()


@persistent
def fas_on_load(_dummy=None):
    _scene_count[0] = 0
    check_scenes()
    note_ranges()
    # A Save As to another folder stored a path back to the old folder.
    if bpy.data.filepath:
        _repoint("when the file opened")


@persistent
def fas_before_save(filepath="", *_args):
    """The file stores the path beside it, so a first save isn't left with changes."""
    if filepath:
        _repoint("before saving", saved=True)


@persistent
def fas_after_save(_filepath="", *_args):
    _repoint("after saving")


_HANDLERS = (
    ("depsgraph_update_post", "fas_scene_watch"),
    ("load_post", "fas_on_load"),
    ("save_pre", "fas_before_save"),
    ("save_post", "fas_after_save"),
)


def register():
    _scene_count[0] = len(bpy.data.scenes) if hasattr(bpy.data, "scenes") else 0
    _ranges.clear()
    for handler_list, name in _HANDLERS:
        handlers, fn = getattr(bpy.app.handlers, handler_list), globals()[name]
        if fn not in handlers:
            handlers.append(fn)


def unregister():
    for handler_list, name in _HANDLERS:
        handlers, fn = getattr(bpy.app.handlers, handler_list), globals()[name]
        if fn in handlers:
            handlers.remove(fn)
