# SPDX-License-Identifier: GPL-3.0-or-later
"""The fire's light: a point light that flickers through a Noise F-curve modifier,
so it changes over frames with no drivers, handlers or Python running.

The flicker is stored on the light as a share of its energy, so a Light Strength of 0
and back gives the built flicker again.  Scaling the noise by new / old energy lost it
for good at 0.
"""

import bpy

FLICKER_PROP = "fas_flicker"
DEFAULT_FLICKER = 0.3


def _energy_fcurve(light_data):
    light_data.keyframe_insert("energy", frame=1)
    animation = light_data.animation_data
    action = animation.action
    if getattr(animation, "action_slot", None) is not None:
        strip = action.layers[0].strips[0]
        return strip.channelbag(animation.action_slot).fcurves[0], action
    return action.fcurves[0], action


def _existing_fcurve(light_data):
    animation = light_data.animation_data
    if animation is None or animation.action is None:
        return None
    if getattr(animation, "action_slot", None) is not None:
        fcurves = animation.action.layers[0].strips[0].channelbag(animation.action_slot).fcurves
    else:
        fcurves = animation.action.fcurves
    return next((f for f in fcurves if f.data_path == "energy"), None)


def get_energy(light_data):
    fcurve = _existing_fcurve(light_data)
    return fcurve.keyframe_points[0].co.y if fcurve is not None else light_data.energy


def flicker_ratio(light_data, fcurve=None):
    """The flicker as a share of the energy.  A light from before the share was stored
    gets it worked out once from its curve; one whose flicker was already lost at 0
    gets the default back."""
    stored = light_data.get(FLICKER_PROP)
    if stored is not None:
        return float(stored)
    fcurve = fcurve or _existing_fcurve(light_data)
    noise = next((m for m in fcurve.modifiers if m.type == "NOISE"), None) if fcurve is not None else None
    if noise is None:
        return 0.0
    old = fcurve.keyframe_points[0].co.y
    ratio = noise.strength / old if old and noise.strength else DEFAULT_FLICKER
    light_data[FLICKER_PROP] = ratio
    return ratio


def set_energy(light_data, energy, flicker=None):
    """Change the light's strength; the flicker keeps its share of it, whatever the energy."""
    fcurve = _existing_fcurve(light_data)
    if fcurve is None:
        light_data.energy = energy
        return
    if flicker is not None:
        light_data[FLICKER_PROP] = flicker
    ratio = flicker_ratio(light_data, fcurve)
    point = fcurve.keyframe_points[0]
    point.co.y = energy
    point.handle_left.y = energy
    point.handle_right.y = energy
    for modifier in fcurve.modifiers:
        if modifier.type == "NOISE":
            modifier.strength = energy * ratio
    fcurve.update()
    light_data.energy = energy


def build_light(name, energy, colour=(1.0, 0.42, 0.13), radius=0.25, flicker=DEFAULT_FLICKER, speed=3.0,
                seed=0.0):
    """The light object (not linked anywhere yet) and its action."""
    data = bpy.data.lights.new(name, "POINT")
    data.energy = energy
    data[FLICKER_PROP] = flicker
    data.color = colour
    data.shadow_soft_size = radius
    fcurve, action = _energy_fcurve(data)
    noise = fcurve.modifiers.new("NOISE")
    noise.strength = energy * flicker
    noise.scale = speed
    noise.phase = seed
    noise.depth = 1
    return bpy.data.objects.new(name, data), action
