# SPDX-License-Identifier: GPL-3.0-or-later
"""Building an effect: everything it makes is tagged, collected and recorded."""

import bpy

from ..core import bounces, naming, registry, view_sync
from . import fire_light, light_mode, plane_stack


def plane_estimate(sites, layers, has_glow, on_mesh):
    planes = sites * layers + (1 if has_glow else 0)
    # Random scatter can land a little over its density, so leave room.
    return planes * 2 if on_mesh else planes


def create_plane_effect(context, kind, name, material, stack, location, glow=None, light=None,
                        mode=light_mode.REAL, source=None, density=0.0):
    """A plane stack with an optional fire light.  Returns the new entry's uuid."""
    scene = context.scene
    effect_uuid = naming.new_uuid()
    naming.tag(material, kind, effect_uuid)
    if glow is not None:
        naming.tag(glow, kind, effect_uuid)
    collection = naming.new_effect_collection(scene, kind, effect_uuid, name)

    tree = plane_stack.build_tree(f"FAS_{name}", material, glow, on_mesh=source is not None)
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
    inputs = {**stack, "Face Viewport": True, "View Target": target}
    if source is not None:
        inputs.update({"Source": source, "Density": density, "Standoff": stack["Width"] * 0.5})
    plane_stack.set_inputs(modifier, inputs)

    entry = registry.add(scene, kind, effect_uuid, primary=obj, root_collection=collection)
    entry.source = source
    entry.sites = stack["Sites"]
    entry.has_glow = glow is not None
    entry.planes = plane_estimate(stack["Sites"], stack["Layers"], glow is not None, source is not None)
    entry.base_width, entry.base_height = stack["Width"], stack["Height"]
    entry.base_spread, entry.base_spacing = stack["Spread"], stack["Spacing"]
    for node_name, base in (("fas_strength", "base_strength"), ("fas_density", "base_density")):
        node = material.node_tree.nodes.get(node_name)
        if node is not None:
            setattr(entry, base, node.outputs[0].default_value)

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
        entry.base_energy = light_obj.data.energy
    light_mode.apply(obj, light_obj, mode)
    entry.light_mode = mode
    entry.seed = stack["Seed"]
    entry.layers = stack["Layers"]

    bounces.after_create(scene)
    return effect_uuid
