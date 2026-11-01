# SPDX-License-Identifier: GPL-3.0-or-later
"""Delete: removes only what an effect owns, and only while it's still the add-on's.

Ownership is the owner tag, never a name.  Anything the buyer adopted (used in another
scene, given a fake user, unparented from the effect) loses its tag and stays.
Anything of the buyer's that was put inside the effect's collection stays in the scene.
"""

import functools

import bpy

from .. import constants as C
from . import bounces, copies, errors, naming, registry

_DATA = ("meshes", "particles", "node_groups", "materials", "actions", "lights")


def _adopted(obj, scene, primary):
    if obj.use_fake_user or any(s != scene for s in obj.users_scene):
        return True
    return primary is not None and obj != primary and obj.parent != primary


def _rescue_contents(scene, collections, effect_uuid):
    """The buyer's own objects and collections inside the effect stay in the scene."""
    for col in collections:
        for obj in list(col.objects):
            if not naming.owned_by(obj, effect_uuid):
                col.objects.unlink(obj)
                if scene not in obj.users_scene:
                    scene.collection.objects.link(obj)
        for child in list(col.children):
            if child not in collections and not naming.owned_by(child, effect_uuid):
                col.children.unlink(child)
                if child not in tuple(scene.collection.children_recursive):
                    scene.collection.children.link(child)


def _owned_objects(effect_uuid):
    return [obj for obj in bpy.data.objects if naming.owned_by(obj, effect_uuid)]


def _remove_object(obj):
    """Remove it; the buyer's children of it keep their place in the world."""
    for child in list(obj.children):
        world = child.matrix_world.copy()
        child.parent = None
        child.matrix_world = world
    bpy.data.objects.remove(obj, do_unlink=True)


def _sweep(scene, entry, effect_uuid):
    primary = entry.primary if entry is not None else None
    collections = [c for c in bpy.data.collections if naming.owned_by(c, effect_uuid)]
    _rescue_contents(scene, collections, effect_uuid)

    objects = _owned_objects(effect_uuid)
    for obj in objects:
        if _adopted(obj, scene, primary):
            for col in collections:
                if obj.name in col.objects:
                    col.objects.unlink(obj)
            if not obj.users_collection:
                scene.collection.objects.link(obj)
            naming.release(obj)
    for obj in _owned_objects(effect_uuid):
        if obj.parent is None or not naming.owned_by(obj.parent, effect_uuid):
            continue
        # Parts go before the primary, so its children loop only meets the buyer's.
        _remove_object(obj)
    for obj in _owned_objects(effect_uuid):
        _remove_object(obj)

    for col in collections:
        bpy.data.collections.remove(col)

    # Dependencies release their users only as they go, so sweep until nothing changes.
    removed = True
    while removed:
        removed = False
        for group in _DATA:
            data = getattr(bpy.data, group)
            for id_block in list(data):
                if (naming.owned_by(id_block, effect_uuid) and id_block.users == 0
                        and not id_block.use_fake_user):
                    data.remove(id_block)
                    removed = True
    # Whatever is left is in use by something of the buyer's.
    for group in _DATA:
        for id_block in getattr(bpy.data, group):
            if naming.owned_by(id_block, effect_uuid):
                naming.release(id_block)


def _detach_from_this_scene(scene, entry):
    """A linked copy shares everything: leave the objects to the other scene."""
    col = entry.root_collection
    if col is None:
        return
    for root in list(scene.collection.children):
        if root.get(C.ROOT_PROP) and col in tuple(root.children):
            scene.collection.children.unlink(root)
            # Other effects in the shared root stay in this scene.
            for other in scene.fas_effects:
                keep = other.root_collection
                if other.uuid != entry.uuid and keep is not None and keep in tuple(root.children):
                    scene.collection.children.link(keep)
            return
    if col in tuple(scene.collection.children):
        scene.collection.children.unlink(col)


def _prune(scene):
    """Drop what only existed for effects: the empty root and the view target."""
    if not len(scene.fas_effects):
        target = scene.fas_view_target
        if target is not None:
            scene.fas_view_target = None
            if not any(s != scene for s in target.users_scene):
                bpy.data.objects.remove(target, do_unlink=True)
    for root in list(scene.collection.children):
        if root.get(C.ROOT_PROP) and not root.children and not root.objects:
            bpy.data.collections.remove(root)


def delete_effect(scene, effect_uuid):
    """Returns the bounce limit's outcome, for reporting."""
    copies.reidentify()
    entry = registry.get(scene, effect_uuid)
    shared = entry is not None and any(
        registry.get(other, effect_uuid) is not None
        for other in bpy.data.scenes if other != scene)
    if shared:
        _detach_from_this_scene(scene, entry)
    else:
        _sweep(scene, entry, effect_uuid)
    registry.remove(scene, effect_uuid)
    _prune(scene)
    return bounces.after_delete(scene)


def _owner_uuids():
    found = set()
    for group in ("objects", "collections") + _DATA:
        for id_block in getattr(bpy.data, group):
            v = id_block.get(C.OWNER_PROP, "")
            if isinstance(v, str) and ":" in v:
                found.add(v.rsplit(":", 1)[1])
    return found


def guarded_create(execute):
    """Decorator for Create operators.

    An operator that returns CANCELLED (or raises) doesn't roll back what it already
    built, and a half-built effect may have no entry to delete it by.  On failure,
    sweep every uuid that appeared during this call.
    """
    @functools.wraps(execute)
    def wrapper(self, context):
        before = _owner_uuids()
        try:
            result = execute(self, context)
        except Exception as exc:
            result = errors.fail(self, errors._operator_title(self), exc)
        if "CANCELLED" in result:
            for effect_uuid in _owner_uuids() - before:
                delete_effect(context.scene, effect_uuid)
        return result
    return wrapper


class FAS_OT_effect_delete(bpy.types.Operator):
    bl_idname = "fas.effect_delete"
    bl_label = "Delete Effect"
    bl_description = "Remove this effect and only what the add-on made for it"
    bl_options = {"REGISTER", "UNDO", "INTERNAL"}

    uuid: bpy.props.StringProperty(options={"SKIP_SAVE"})

    def execute(self, context):
        message = bounces.describe(delete_effect(context.scene, self.uuid))
        if message:
            self.report({"INFO"}, message)
        return {"FINISHED"}


CLASSES = (FAS_OT_effect_delete,)
