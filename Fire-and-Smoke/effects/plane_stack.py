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
# Sine of the view's elevation where planes start and finish fading.
STEEP_START = 0.55
STEEP_END = 0.92


def _object_location(kit, object_socket):
    info = kit.node("GeometryNodeObjectInfo", transform_space="RELATIVE")
    kit.plug(info.inputs["Object"], object_socket)
    return info.outputs["Location"]


def _facing_target(kit, group_in):
    """Location the planes turn towards, in the effect object's space.

    Final renders are never viewport evaluations, so they always face the camera.
    """
    camera = _object_location(kit, kit.node("GeometryNodeInputActiveCamera").outputs[0])
    view = _object_location(kit, group_in.outputs["View Target"])
    use_view = kit.node("FunctionNodeBooleanMath", operation="AND")
    kit.plug(use_view.inputs[0], kit.node("GeometryNodeIsViewport").outputs[0])
    kit.plug(use_view.inputs[1], group_in.outputs["Face Viewport"])
    switch = kit.node("GeometryNodeSwitch", input_type="VECTOR")
    kit.plug(switch.inputs["Switch"], use_view.outputs[0])
    kit.plug(switch.inputs["False"], camera)
    kit.plug(switch.inputs["True"], view)
    return switch.outputs[0]


def _steepness(kit, target):
    """0 when viewed from the side, 1 when viewed from straight above or below."""
    position = kit.node("GeometryNodeInputPosition").outputs[0]
    to_target = kit.vec("SUBTRACT", target, position)
    _dx, _dy, dz = kit.split(to_target)
    sine = kit.div(kit.math("ABSOLUTE", dz), kit.math("MAXIMUM", kit.vec("LENGTH", to_target), 1e-4))
    return kit.remap(sine, STEEP_START, STEEP_END, smooth=True)


def _store(kit, geometry, name, value, domain="POINT"):
    store = kit.node("GeometryNodeStoreNamedAttribute", data_type="FLOAT", domain=domain)
    kit.plug(store.inputs["Name"], name)
    kit.plug(store.inputs["Geometry"], geometry)
    kit.plug(store.inputs["Value"], value)
    return store.outputs[0]


def _glow_card(kit, group_in, target, material):
    """A flat, soft glow that fades in as the view steepens and the planes fade out."""
    point = kit.node("GeometryNodePoints")
    kit.plug(point.inputs["Count"], 1)
    stored = _store(kit, point.outputs[0], C.ATTR_STEEP, _steepness(kit, target))
    size = kit.mul(kit.add(group_in.outputs["Width"], group_in.outputs["Spread"]), 1.6)
    grid = kit.node("GeometryNodeMeshGrid")
    grid.inputs["Vertices X"].default_value = 2
    grid.inputs["Vertices Y"].default_value = 2
    grid.inputs["Size X"].default_value = 1.0
    grid.inputs["Size Y"].default_value = 1.0
    uv = kit.node("GeometryNodeStoreNamedAttribute", data_type="FLOAT2", domain="CORNER")
    kit.plug(uv.inputs["Name"], C.UV_ATTR)
    kit.plug(uv.inputs["Geometry"], grid.outputs["Mesh"])
    kit.plug(uv.inputs["Value"], grid.outputs["UV Map"])
    lift = kit.node("GeometryNodeTransform")
    lift.inputs["Translation"].default_value = (0.0, 0.0, 0.03)
    kit.plug(lift.inputs["Geometry"], uv.outputs[0])
    set_material = kit.node("GeometryNodeSetMaterial")
    set_material.inputs["Material"].default_value = material
    kit.plug(set_material.inputs["Geometry"], lift.outputs[0])
    instance = kit.node("GeometryNodeInstanceOnPoints")
    kit.plug(instance.inputs["Points"], stored)
    kit.plug(instance.inputs["Instance"], set_material.outputs[0])
    kit.plug(instance.inputs["Scale"], kit.xyz(size, size, 1.0))
    return instance.outputs[0]


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


def build_tree(name, material, glow_material=None):
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
    iface.new_socket("Face Viewport", in_out="INPUT", socket_type="NodeSocketBool",
                     description="Preview only: final renders always face the scene camera")
    iface.new_socket("View Target", in_out="INPUT", socket_type="NodeSocketObject")

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
    target = _facing_target(kit, group_in)
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
    stored = _store(kit, set_position.outputs[0], C.ATTR_LAYER, fraction)
    stored = _store(kit, stored, C.ATTR_STEEP, _steepness(kit, target))

    random = kit.node("FunctionNodeRandomValue", data_type="FLOAT")
    kit.plug(random.inputs["Seed"], group_in.outputs["Seed"])
    stored = _store(kit, stored, C.ATTR_RANDOM, random.outputs["Value"])

    # Spin around the vertical axis only: the plane's front is -Y.
    tx, ty, _tz = kit.split(kit.vec("SUBTRACT", target, position))
    angle = kit.math("ARCTAN2", tx, kit.mul(ty, -1.0))
    site_scale = kit.node("GeometryNodeInputNamedAttribute", data_type="FLOAT")
    kit.plug(site_scale.inputs["Name"], "fas_site_scale")
    site_scale_value = site_scale.outputs["Attribute"]
    scale = kit.xyz(kit.mul(group_in.outputs["Width"], site_scale_value), 1.0,
                    kit.mul(group_in.outputs["Height"], site_scale_value))

    instance = kit.node("GeometryNodeInstanceOnPoints")
    kit.plug(instance.inputs["Points"], stored)
    kit.plug(instance.inputs["Instance"], _plane(kit, material))
    kit.plug(instance.inputs["Rotation"], kit.xyz(0.0, 0.0, angle))
    kit.plug(instance.inputs["Scale"], scale)

    geometry = instance.outputs[0]
    if glow_material is not None:
        join = kit.node("GeometryNodeJoinGeometry")
        kit.plug(join.inputs[0], _glow_card(kit, group_in, target, glow_material))
        kit.plug(join.inputs[0], geometry)
        geometry = join.outputs[0]

    time = kit.node("GeometryNodeInputSceneTime")
    stored_time = _store(kit, geometry, C.ATTR_TIME, time.outputs["Seconds"], domain="INSTANCE")
    kit.plug(group_out.inputs[0], stored_time)
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
