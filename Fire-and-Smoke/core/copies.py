# SPDX-License-Identifier: GPL-3.0-or-later
"""Copied scenes.

A full scene copy duplicates objects, meshes, lights, actions and collections, but
shares node trees and materials, and it copies the uuid and every owner tag too.
The copy gets its own uuid and its own trees and materials, so deleting in either
scene can't reach the other.  A linked copy shares its objects with the original, so
it keeps the uuid and Delete only detaches it.

A full copy also shares a simulated fire's cache folder, so the copy's domain gets the
path for its new uuid.
"""

import bpy

from . import cache_folder, naming


def _own_material(material, old, new, kind, seen):
    if material is None or not naming.owned_by(material, old):
        return material
    if material not in seen:
        seen[material] = naming.tag(material.copy(), kind, new)
    return seen[material]


def _own_tree(modifier, old, new, kind, seen):
    tree = modifier.node_group
    if tree is None or not naming.owned_by(tree, old):
        return
    tree = tree.copy()
    naming.tag(tree, kind, new)
    modifier.node_group = tree
    for node in tree.nodes:
        for socket in node.inputs:
            if socket.bl_idname == "NodeSocketMaterial":
                socket.default_value = _own_material(socket.default_value, old, new, kind, seen)


def _own_animation(data, old, new, kind):
    animation = getattr(data, "animation_data", None)
    action = animation.action if animation is not None else None
    if action is None or not naming.owned_by(action, old):
        return
    if action.users > 1:
        slot_name = animation.action_slot.name_display if hasattr(animation, "action_slot") else None
        action = action.copy()
        animation.action = action
        if slot_name is not None and animation.action_slot is None:
            animation.action_slot = next(s for s in action.slots if s.name_display == slot_name)
    naming.tag(action, kind, new)


def _own_object(obj, old, new, kind, seen):
    naming.tag(obj, kind, new)
    data = obj.data
    if data is not None and naming.owned_by(data, old):
        if data.users > 1:
            data = data.copy()
            obj.data = data
        naming.tag(data, kind, new)
        _own_animation(data, old, new, kind)
    for modifier in obj.modifiers:
        if modifier.type == "NODES":
            _own_tree(modifier, old, new, kind, seen)
    for slot in obj.material_slots:
        if slot.material is not None:
            slot.material = _own_material(slot.material, old, new, kind, seen)
    for system in obj.particle_systems:
        settings = system.settings
        if settings is not None and naming.owned_by(settings, old):
            if settings.users > 1:
                settings = settings.copy()
                system.settings = settings
            naming.tag(settings, kind, new)


def _split(entry):
    old, new, kind = entry.uuid, naming.new_uuid(), entry.kind
    entry.uuid = new
    seen = {}
    root = entry.root_collection
    if root is None:
        return
    for col in (root, *root.children_recursive):
        if naming.owned_by(col, old):
            naming.tag(col, kind, new)
    for obj in root.all_objects:
        if naming.owned_by(obj, old):
            _own_object(obj, old, new, kind, seen)
    cache_folder.repoint(entry)
    # Shared particle settings pointed at the original's spark.
    if entry.instance is not None and entry.primary is not None:
        for system in entry.primary.particle_systems:
            system.settings.instance_object = entry.instance


def reidentify():
    """Give every full copy's effects their own identity.  Returns how many split."""
    seen = {}
    split = 0
    for scene in bpy.data.scenes:
        for entry in scene.fas_effects:
            first = seen.setdefault(entry.uuid, entry.primary)
            if first is not entry.primary and first != entry.primary:
                _split(entry)
                split += 1
    return split
