# SPDX-License-Identifier: GPL-3.0-or-later
"""Naming, ownership tagging, and managed-collection helpers."""

import uuid as _uuid

import bpy

from .. import constants as C


def new_uuid():
    return _uuid.uuid4().hex


def short(u):
    return u[:8]


def owner_tag(kind, effect_uuid):
    return f"{kind}:{effect_uuid}"


def tag(id_block, kind, effect_uuid):
    """Stamp any ID datablock as owned by an effect."""
    id_block[C.OWNER_PROP] = owner_tag(kind, effect_uuid)
    return id_block


def owned_by(id_block, effect_uuid):
    v = id_block.get(C.OWNER_PROP, "")
    return isinstance(v, str) and v.endswith(":" + effect_uuid)


def release(id_block):
    """It's the buyer's now: no later sweep can touch it."""
    if C.OWNER_PROP in id_block.keys():
        del id_block[C.OWNER_PROP]


def ensure_root_collection(scene):
    """This scene's own managed root; a root shared with another scene doesn't count."""
    for root in scene.collection.children:
        shared = any(other != scene and root in tuple(other.collection.children_recursive)
                     for other in bpy.data.scenes)
        if root.get(C.ROOT_PROP) and not shared:
            return root
    root = bpy.data.collections.new(C.ROOT_COLLECTION)
    root[C.ROOT_PROP] = True
    scene.collection.children.link(root)
    return root


def new_effect_collection(scene, kind, effect_uuid):
    root = ensure_root_collection(scene)
    col = bpy.data.collections.new(f"{C.KIND_LABELS.get(kind, kind)} {short(effect_uuid)}")
    tag(col, kind, effect_uuid)
    root.children.link(col)
    return col
