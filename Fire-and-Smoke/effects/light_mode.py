# SPDX-License-Identifier: GPL-3.0-or-later
"""How a fire lights its scene: the owned light, the planes' own emission, or both.

Real is the default and the only mode that matches between engines.  Emissive
lighting depends on the render engine bouncing emission around the scene, so it is
Cycles-focused.
"""

import bpy

REAL = "REAL"
EMISSIVE = "EMISSIVE"
BOTH = "BOTH"
ITEMS = (
    (REAL, "Real", "A flickering light that looks the same in Cycles and EEVEE", 0),
    (EMISSIVE, "Emissive", "The flames themselves light the scene. Cycles-focused: "
                           "EEVEE shows little of this light", 1),
    (BOTH, "Both", "The light and the flames together. The flames' share is Cycles-focused", 2),
)


def apply(fire, light, mode):
    """Set what lights the scene.  Planes never cast shadows in any mode."""
    planes_light = mode in (EMISSIVE, BOTH)
    fire.visible_shadow = False
    fire.visible_diffuse = planes_light
    fire.visible_glossy = planes_light
    if light is not None:
        hidden = mode == EMISSIVE
        light.hide_render = hidden
        light.hide_viewport = hidden


def _fire_and_light(obj):
    if obj is None or not any(m.type == "NODES" for m in obj.modifiers):
        return None, None
    return obj, next((c for c in obj.children if c.type == "LIGHT"), None)


class FAS_OT_light_mode(bpy.types.Operator):
    bl_idname = "fas.light_mode"
    bl_label = "Set Fire Light Mode"
    bl_description = "Choose what lights the scene for the selected fire"
    bl_options = {"REGISTER", "UNDO"}

    mode: bpy.props.EnumProperty(name="Light", items=ITEMS, options={"SKIP_SAVE"})

    def execute(self, context):
        fire, light = _fire_and_light(context.active_object)
        if fire is None:
            self.report({"ERROR"}, "Select a fire first")
            return {"CANCELLED"}
        apply(fire, light, self.mode)
        return {"FINISHED"}


CLASSES = (FAS_OT_light_mode,)
