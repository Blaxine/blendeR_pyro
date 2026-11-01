# SPDX-License-Identifier: GPL-3.0-or-later
"""The fire's light: a point light that flickers through a Noise F-curve modifier,
so it changes over frames with no drivers, handlers or Python running."""

import bpy


def _energy_fcurve(light_data):
    light_data.keyframe_insert("energy", frame=1)
    animation = light_data.animation_data
    action = animation.action
    if getattr(animation, "action_slot", None) is not None:
        strip = action.layers[0].strips[0]
        return strip.channelbag(animation.action_slot).fcurves[0], action
    return action.fcurves[0], action


def build_light(name, energy, colour=(1.0, 0.42, 0.13), radius=0.25, flicker=0.3, speed=3.0, seed=0.0):
    """The light object (not linked anywhere yet) and its action."""
    data = bpy.data.lights.new(name, "POINT")
    data.energy = energy
    data.color = colour
    data.shadow_soft_size = radius
    fcurve, action = _energy_fcurve(data)
    noise = fcurve.modifiers.new("NOISE")
    noise.strength = energy * flicker
    noise.scale = speed
    noise.phase = seed
    noise.depth = 1
    return bpy.data.objects.new(name, data), action
