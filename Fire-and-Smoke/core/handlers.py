# SPDX-License-Identifier: GPL-3.0-or-later
"""App handlers: when the scenes change, copied effects are re-identified straight away."""

import bpy
from bpy.app.handlers import persistent

from . import copies, errors

_scene_count = [0]


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


@persistent
def fas_scene_watch(_scene, _depsgraph=None):
    check_scenes()


@persistent
def fas_on_load(_dummy=None):
    _scene_count[0] = 0
    check_scenes()


def register():
    _scene_count[0] = len(bpy.data.scenes) if hasattr(bpy.data, "scenes") else 0
    if fas_scene_watch not in bpy.app.handlers.depsgraph_update_post:
        bpy.app.handlers.depsgraph_update_post.append(fas_scene_watch)
    if fas_on_load not in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.append(fas_on_load)


def unregister():
    if fas_scene_watch in bpy.app.handlers.depsgraph_update_post:
        bpy.app.handlers.depsgraph_update_post.remove(fas_scene_watch)
    if fas_on_load in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.remove(fas_on_load)
