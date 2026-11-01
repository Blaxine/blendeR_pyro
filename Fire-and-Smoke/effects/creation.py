# SPDX-License-Identifier: GPL-3.0-or-later
"""Building an effect: everything it makes is tagged, collected and recorded."""

import bpy

from ..core import bounces, naming, registry, view_sync
from . import fire_light, light_mode, plane_stack


def planes_of(stack, has_glow):
    return stack["Sites"] * stack["Layers"] + (1 if has_glow else 0)


def create_plane_effect(context, kind, name, material, stack, location, glow=None, light=None,
                        mode=light_mode.REAL):
    """A plane stack with an optional fire light.  Returns the new entry's uuid."""
    scene = context.scene
    effect_uuid = naming.new_uuid()
    naming.tag(material, kind, effect_uuid)
    if glow is not None:
        naming.tag(glow, kind, effect_uuid)
    collection = naming.new_effect_collection(scene, kind, effect_uuid)

    tree = plane_stack.build_tree(f"FAS_{name}", material, glow)
    naming.tag(tree, kind, effect_uuid)
    mesh = bpy.data.meshes.new(name)
    naming.tag(mesh, kind, effect_uuid)
    obj = bpy.data.objects.new(name, mesh)
    naming.tag(obj, kind, effect_uuid)
    obj.location = location
    collection.objects.link(obj)

    target = view_sync.ensure_target(scene)
    modifier = obj.modifiers.new(name, "NODES")
    modifier.node_group = tree
    plane_stack.set_inputs(modifier, {**stack, "Face Viewport": True, "View Target": target})

    entry = registry.add(scene, kind, effect_uuid, primary=obj, root_collection=collection)
    entry.planes = planes_of(stack, glow is not None)

    light_obj = None
    if light is not None:
        height = light.pop("height", stack["Height"] * 0.4)
        light_obj, action = fire_light.build_light(f"{name} Light", **light)
        naming.tag(light_obj, kind, effect_uuid)
        naming.tag(light_obj.data, kind, effect_uuid)
        naming.tag(action, kind, effect_uuid)
        collection.objects.link(light_obj)
        light_obj.parent = obj
        light_obj.location = (0.0, 0.0, height)
        entry.light = light_obj
    light_mode.apply(obj, light_obj, mode)
    entry.light_mode = mode

    bounces.after_create(scene)
    return effect_uuid
