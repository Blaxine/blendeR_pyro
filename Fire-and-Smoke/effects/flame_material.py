# SPDX-License-Identifier: GPL-3.0-or-later
"""The flame material: noise-driven emission and transparency, with no images."""

import bpy

from .. import constants as C
from .nodekit import Kit

INDIRECT_BOOST = 15.0
FLAME_STOPS = (
    (0.02, (0.80, 0.030, 0.000, 1.0)),
    (0.28, (1.00, 0.115, 0.002, 1.0)),
    (0.62, (1.00, 0.30, 0.008, 1.0)),
    (1.00, (1.00, 0.60, 0.07, 1.0)),
)


def plane_inputs(kit):
    """(u, v, layer, random, time, steepness) from the plane stack's attributes."""
    uv = kit.node("ShaderNodeAttribute", attribute_type="GEOMETRY", attribute_name=C.UV_ATTR)
    u, v, _w = kit.split(uv.outputs["Vector"])
    attrs = []
    for name in (C.ATTR_LAYER, C.ATTR_RANDOM, C.ATTR_TIME, C.ATTR_STEEP):
        node = kit.node("ShaderNodeAttribute", attribute_type="INSTANCER", attribute_name=name)
        attrs.append(node.outputs["Fac"])
    return (u, v, *attrs)


def noise(kit, vector, w, scale, detail=4.0, roughness=0.5, distortion=0.0):
    node = kit.node("ShaderNodeTexNoise", noise_dimensions="4D")
    kit.plug(node.inputs["Vector"], vector)
    kit.plug(node.inputs["W"], w)
    kit.plug(node.inputs["Scale"], scale)
    kit.plug(node.inputs["Detail"], detail)
    kit.plug(node.inputs["Roughness"], roughness)
    kit.plug(node.inputs["Distortion"], distortion)
    return node.outputs["Fac"]


def build_flame_material(name, speed=1.35, strength=0.8, steep_floor=0.0):
    material = bpy.data.materials.new(name)
    material.use_nodes = True
    material.surface_render_method = "BLENDED"
    tree = material.node_tree
    tree.nodes.clear()
    kit = Kit(tree)
    u, v, layer, rand, time, steep = plane_inputs(kit)

    # The whole tongue sways more towards its tip.
    sway_at = kit.xyz(kit.mul(rand, 37.0), kit.sub(kit.mul(v, 1.1), kit.mul(time, 0.8)), 0.0)
    sway = kit.sub(noise(kit, sway_at, kit.mul(time, 0.3), 1.6, detail=1.0), 0.5)
    x = kit.add(kit.sub(u, 0.5), kit.mul(kit.mul(sway, 0.55), v))

    # Noise stretched upward and scrolling up reads as licking flame.
    rise = kit.sub(kit.mul(v, 1.15), kit.mul(time, speed))
    at = kit.xyz(kit.add(kit.mul(x, 2.6), kit.mul(rand, 11.0)), rise,
                 kit.add(kit.mul(layer, 2.5), kit.mul(rand, 7.0)))
    fine = noise(kit, at, kit.mul(time, 0.4), 2.7, detail=6.0, roughness=0.56, distortion=0.25)

    # Teardrop: wide low down, closing at the tip, and soft at the base.
    half_width = kit.add(kit.mul(kit.math("POWER", kit.sub(1.0, v), 0.75), 0.44), 0.005)
    across = kit.div(kit.math("ABSOLUTE", x), half_width)
    shape = kit.mul(kit.remap(across, 1.0, 0.0, smooth=True), kit.remap(v, 0.0, 0.16, smooth=True))

    # Erode the shape with noise, more strongly towards the tip.
    erode = kit.mul(kit.sub(fine, 0.5), kit.add(1.25, kit.mul(v, 2.2)))
    density = kit.sub(kit.add(kit.mul(shape, 1.05), erode), kit.mul(v, 0.5))

    # From steep angles the planes would read as thin slices, so they fade out.
    fade = kit.sub(1.0, kit.mul(steep, 1.0 - steep_floor))
    alpha = kit.mul(kit.remap(density, 0.14, 0.34, smooth=True), fade)
    colour = kit.ramp(kit.remap(density, 0.12, 1.0), FLAME_STOPS)

    emission = kit.node("ShaderNodeEmission")
    kit.plug(emission.inputs["Color"], colour)
    strength_value = kit.node("ShaderNodeValue", name="fas_strength")
    strength_value.outputs[0].default_value = strength
    # In Emissive and Both, the flames light the scene harder than they look.
    light_path = kit.node("ShaderNodeLightPath")
    indirect = kit.remap(light_path.outputs["Is Camera Ray"], 0.0, 1.0, INDIRECT_BOOST, 1.0)
    kit.plug(emission.inputs["Strength"], kit.mul(strength_value.outputs[0], indirect))

    transparent = kit.node("ShaderNodeBsdfTransparent")
    mix = kit.node("ShaderNodeMixShader")
    kit.plug(mix.inputs[0], alpha)
    kit.plug(mix.inputs[1], transparent.outputs[0])
    kit.plug(mix.inputs[2], emission.outputs[0])
    output = kit.node("ShaderNodeOutputMaterial")
    kit.plug(output.inputs["Surface"], mix.outputs[0])
    return material


def build_glow_material(name, colour=(1.0, 0.16, 0.012, 1.0), strength=1.1):
    """The soft glow that replaces the planes from steep angles."""
    material = bpy.data.materials.new(name)
    material.use_nodes = True
    material.surface_render_method = "BLENDED"
    tree = material.node_tree
    tree.nodes.clear()
    kit = Kit(tree)
    u, v, _layer, _rand, time, steep = plane_inputs(kit)

    across = kit.vec("LENGTH", kit.xyz(kit.sub(u, 0.5), kit.sub(v, 0.5), 0.0))
    at = kit.xyz(kit.mul(u, 3.0), kit.mul(v, 3.0), 0.0)
    breathing = kit.remap(noise(kit, at, kit.mul(time, 1.2), 1.5, detail=2.0), 0.3, 0.7, 0.55, 1.0)
    alpha = kit.mul(kit.mul(kit.remap(across, 0.5, 0.0, smooth=True), steep), breathing)

    emission = kit.node("ShaderNodeEmission")
    emission.inputs["Color"].default_value = colour
    emission.inputs["Strength"].default_value = strength
    transparent = kit.node("ShaderNodeBsdfTransparent")
    mix = kit.node("ShaderNodeMixShader")
    kit.plug(mix.inputs[0], alpha)
    kit.plug(mix.inputs[1], transparent.outputs[0])
    kit.plug(mix.inputs[2], emission.outputs[0])
    output = kit.node("ShaderNodeOutputMaterial")
    kit.plug(output.inputs["Surface"], mix.outputs[0])
    return material
