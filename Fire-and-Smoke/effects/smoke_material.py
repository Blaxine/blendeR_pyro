# SPDX-License-Identifier: GPL-3.0-or-later
"""The smoke material: billowing noise that carries its own shading.

Smoke doesn't react to scene lights.  Its light and dark come from the noise, so it
looks the same in Cycles and EEVEE whatever the scene's lighting does.
"""

import bpy

from .flame_material import noise, plane_inputs
from .nodekit import Kit


def build_smoke_material(name, dark=(0.03, 0.03, 0.03, 1.0), light=(0.22, 0.22, 0.23, 1.0),
                         density=0.5, speed=0.28, scale=1.9, base_width=0.1, top_width=0.5, aspect=1.5):
    material = bpy.data.materials.new(name)
    material.use_nodes = True
    material.diffuse_color = (light[0], light[1], light[2], 0.1)  # what Solid view shows
    material.surface_render_method = "BLENDED"
    tree = material.node_tree
    tree.nodes.clear()
    kit = Kit(tree)
    u, v, layer, rand, time, steep = plane_inputs(kit)

    # The plume leans and wanders more as it rises.
    wander_at = kit.xyz(kit.mul(rand, 23.0), kit.sub(kit.mul(v, aspect), kit.mul(time, speed * 0.5)), 0.0)
    wander = kit.sub(noise(kit, wander_at, kit.mul(time, 0.1), 0.9, detail=2.0), 0.5)
    x = kit.add(kit.sub(u, 0.5), kit.mul(kit.mul(wander, 0.9), v))

    # Billows: rising, slowly changing, and larger towards the top.
    rise = kit.sub(kit.mul(v, aspect), kit.mul(time, speed))
    at = kit.xyz(kit.add(kit.mul(x, 1.7), kit.mul(rand, 9.0)), rise,
                 kit.add(kit.mul(layer, 0.8), kit.mul(rand, 5.0)))
    billow_scale = kit.div(scale, kit.add(1.0, kit.mul(v, 0.9)))
    billow = noise(kit, at, kit.mul(time, 0.1), billow_scale, detail=6.0, roughness=0.55, distortion=0.12)

    half_width = kit.add(base_width, kit.mul(kit.sub(top_width, base_width), kit.math("POWER", v, 0.65)))
    edge = kit.remap(kit.div(kit.math("ABSOLUTE", x), half_width), 1.0, 0.0)
    ends = kit.mul(kit.remap(v, 0.0, 0.1, smooth=True), kit.remap(v, 1.0, 0.62, smooth=True))

    # Noise eats the shape from its edges, so the outline is torn rather than smooth.
    body = kit.sub(kit.add(kit.mul(edge, 1.25), kit.mul(kit.sub(billow, 0.5), 2.8)),
                   kit.add(0.3, kit.mul(v, 0.3)))
    inside = kit.remap(edge, 0.0, 0.2, smooth=True)
    amount = kit.mul(kit.mul(kit.remap(body, 0.0, 0.5, smooth=True), inside), ends)
    density_value = kit.node("ShaderNodeValue", name="fas_density")
    density_value.outputs[0].default_value = density
    alpha = kit.mul(kit.mul(amount, density_value.outputs[0]), kit.sub(1.0, kit.mul(steep, 0.75)))

    # Lit tops of the billows, dark hollows between them.
    shade = kit.remap(billow, 0.38, 0.68, smooth=True)
    mix_colour = kit.node("ShaderNodeMix", data_type="RGBA")
    kit.plug(mix_colour.inputs["Factor"], shade)
    kit.plug(mix_colour.inputs["A"], dark)
    kit.plug(mix_colour.inputs["B"], light)

    emission = kit.node("ShaderNodeEmission")
    kit.plug(emission.inputs["Color"], mix_colour.outputs["Result"])
    kit.plug(emission.inputs["Strength"], 1.0)
    transparent = kit.node("ShaderNodeBsdfTransparent")
    mix = kit.node("ShaderNodeMixShader")
    kit.plug(mix.inputs[0], alpha)
    kit.plug(mix.inputs[1], transparent.outputs[0])
    kit.plug(mix.inputs[2], emission.outputs[0])
    output = kit.node("ShaderNodeOutputMaterial")
    kit.plug(output.inputs["Surface"], mix.outputs[0])
    return material
