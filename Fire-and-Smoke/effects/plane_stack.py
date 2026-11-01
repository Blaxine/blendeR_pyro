# SPDX-License-Identifier: GPL-3.0-or-later
"""The plane stack: camera-facing planes built with Geometry Nodes.

Sites spread over a disk, and each site stacks ``Layers`` planes along the
direction to the camera.  Planes spin around the vertical axis only.  All
randomness is a pure function of index and seed, so a frame always evaluates the
same and scrubbing needs no cache.
"""

import math

import bpy

from .. import constants as C
from .nodekit import Kit

GOLDEN_ANGLE = math.pi * (3.0 - math.sqrt(5.0))


def _facing_target(kit):
    """Location the planes turn towards, in the effect object's space."""
    camera = kit.node("GeometryNodeInputActiveCamera")
    info = kit.node("GeometryNodeObjectInfo", transform_space="RELATIVE")
    kit.plug(info.inputs["Object"], camera.outputs[0])
    return info.outputs["Location"]


def _sites(kit, sites, spread):
    """Points on a golden-angle spiral: even cover with one at the centre."""
    index = kit.node("GeometryNodeInputIndex").outputs[0]
    fraction = kit.div(index, kit.math("MAXIMUM", kit.sub(sites, 1), 1))
    radius = kit.mul(spread, kit.math("SQRT", fraction))
    angle = kit.mul(index, GOLDEN_ANGLE)
    position = kit.xyz(kit.mul(radius, kit.math("COSINE", angle)),
                       kit.mul(radius, kit.math("SINE", angle)), 0.0)
    points = kit.node("GeometryNodePoints")
    kit.plug(points.inputs["Count"], sites)
    kit.plug(points.inputs["Position"], position)
    # Outer sites burn lower, which rounds the fire's silhouette.
    falloff = kit.remap(fraction, 0.0, 1.0, 1.0, 0.55)
    store = kit.node("GeometryNodeStoreNamedAttribute", data_type="FLOAT", domain="POINT")
    kit.plug(store.inputs["Name"], "fas_site_scale")
    kit.plug(store.inputs["Geometry"], points.outputs[0])
    kit.plug(store.inputs["Value"], falloff)
    return store.outputs[0]


def _plane(kit, material):
    grid = kit.node("GeometryNodeMeshGrid")
    grid.inputs["Size X"].default_value = 1.0
    grid.inputs["Size Y"].default_value = 1.0
    grid.inputs["Vertices X"].default_value = 2
    grid.inputs["Vertices Y"].default_value = 2
    uv = kit.node("GeometryNodeStoreNamedAttribute", data_type="FLOAT2", domain="CORNER")
    kit.plug(uv.inputs["Name"], C.UV_ATTR)
    kit.plug(uv.inputs["Geometry"], grid.outputs["Mesh"])
    kit.plug(uv.inputs["Value"], grid.outputs["UV Map"])
    # Upright, with the base on the effect's origin.
    upright = kit.node("GeometryNodeTransform")
    upright.inputs["Rotation"].default_value = (math.pi / 2, 0.0, 0.0)
    upright.inputs["Translation"].default_value = (0.0, 0.0, 0.5)
    kit.plug(upright.inputs["Geometry"], uv.outputs[0])
    set_material = kit.node("GeometryNodeSetMaterial")
    set_material.inputs["Material"].default_value = material
    kit.plug(set_material.inputs["Geometry"], upright.outputs[0])
    return set_material.outputs[0]


def build_tree(name, material):
    """A modifier node tree whose settings are its modifier inputs."""
    tree = bpy.data.node_groups.new(name, "GeometryNodeTree")
    tree.is_modifier = True
    iface = tree.interface
    iface.new_socket("Geometry", in_out="OUTPUT", socket_type="NodeSocketGeometry")
    iface.new_socket("Sites", in_out="INPUT", socket_type="NodeSocketInt")
    iface.new_socket("Layers", in_out="INPUT", socket_type="NodeSocketInt")
    iface.new_socket("Spread", in_out="INPUT", socket_type="NodeSocketFloat")
    iface.new_socket("Spacing", in_out="INPUT", socket_type="NodeSocketFloat")
    iface.new_socket("Width", in_out="INPUT", socket_type="NodeSocketFloat")
    iface.new_socket("Height", in_out="INPUT", socket_type="NodeSocketFloat")
    iface.new_socket("Seed", in_out="INPUT", socket_type="NodeSocketInt")

    kit = Kit(tree)
    group_in = kit.node("NodeGroupInput")
    group_out = kit.node("NodeGroupOutput")
    sites, layers = group_in.outputs["Sites"], group_in.outputs["Layers"]

    points = _sites(kit, sites, group_in.outputs["Spread"])

    duplicate = kit.node("GeometryNodeDuplicateElements", domain="POINT")
    kit.plug(duplicate.inputs["Geometry"], points)
    kit.plug(duplicate.inputs["Amount"], layers)
    layer_index = duplicate.outputs["Duplicate Index"]

    # Spread the layers along the flattened direction to the target.
    target = _facing_target(kit)
    position = kit.node("GeometryNodeInputPosition").outputs[0]
    dx, dy, _dz = kit.split(kit.vec("SUBTRACT", target, position))
    flat = kit.vec("NORMALIZE", kit.xyz(dx, dy, 0.0))
    centred = kit.sub(layer_index, kit.div(kit.sub(layers, 1), 2.0))
    offset = kit.vec("SCALE", flat, scale=kit.mul(centred, group_in.outputs["Spacing"]))
    set_position = kit.node("GeometryNodeSetPosition")
    kit.plug(set_position.inputs["Geometry"], duplicate.outputs["Geometry"])
    kit.plug(set_position.inputs["Offset"], offset)

    # Per-plane data for the material.
    fraction = kit.div(layer_index, kit.math("MAXIMUM", kit.sub(layers, 1), 1))
    store_layer = kit.node("GeometryNodeStoreNamedAttribute", data_type="FLOAT", domain="POINT")
    kit.plug(store_layer.inputs["Name"], C.ATTR_LAYER)
    kit.plug(store_layer.inputs["Geometry"], set_position.outputs[0])
    kit.plug(store_layer.inputs["Value"], fraction)

    random = kit.node("FunctionNodeRandomValue", data_type="FLOAT")
    kit.plug(random.inputs["Seed"], group_in.outputs["Seed"])
    store_random = kit.node("GeometryNodeStoreNamedAttribute", data_type="FLOAT", domain="POINT")
    kit.plug(store_random.inputs["Name"], C.ATTR_RANDOM)
    kit.plug(store_random.inputs["Geometry"], store_layer.outputs[0])
    kit.plug(store_random.inputs["Value"], random.outputs["Value"])

    # Spin around the vertical axis only: the plane's front is -Y.
    tx, ty, _tz = kit.split(kit.vec("SUBTRACT", target, position))
    angle = kit.math("ARCTAN2", tx, kit.mul(ty, -1.0))
    site_scale = kit.node("GeometryNodeInputNamedAttribute", data_type="FLOAT")
    kit.plug(site_scale.inputs["Name"], "fas_site_scale")
    site_scale_value = site_scale.outputs["Attribute"]
    scale = kit.xyz(kit.mul(group_in.outputs["Width"], site_scale_value), 1.0,
                    kit.mul(group_in.outputs["Height"], site_scale_value))

    instance = kit.node("GeometryNodeInstanceOnPoints")
    kit.plug(instance.inputs["Points"], store_random.outputs[0])
    kit.plug(instance.inputs["Instance"], _plane(kit, material))
    kit.plug(instance.inputs["Rotation"], kit.xyz(0.0, 0.0, angle))
    kit.plug(instance.inputs["Scale"], scale)

    time = kit.node("GeometryNodeInputSceneTime")
    store_time = kit.node("GeometryNodeStoreNamedAttribute", data_type="FLOAT", domain="INSTANCE")
    kit.plug(store_time.inputs["Name"], C.ATTR_TIME)
    kit.plug(store_time.inputs["Geometry"], instance.outputs[0])
    kit.plug(store_time.inputs["Value"], time.outputs["Seconds"])

    kit.plug(group_out.inputs[0], store_time.outputs[0])
    return tree


def set_input(modifier, name, value):
    """Write one modifier input by its socket name."""
    identifier = modifier.node_group.interface.items_tree[name].identifier
    if hasattr(modifier, "properties"):  # Blender 5.2+: no ID properties on modifiers
        getattr(modifier.properties.inputs, identifier).value = value
    else:
        modifier[identifier] = value


def get_input(modifier, name):
    identifier = modifier.node_group.interface.items_tree[name].identifier
    if hasattr(modifier, "properties"):
        return getattr(modifier.properties.inputs, identifier).value
    return modifier[identifier]


def set_inputs(modifier, values):
    for name, value in values.items():
        set_input(modifier, name, value)
    modifier.node_group.interface_update(bpy.context)


def hide_from_lighting(obj):
    """Planes don't cast shadows, and don't light or reflect in the scene."""
    obj.visible_shadow = False
    obj.visible_diffuse = False
    obj.visible_glossy = False
