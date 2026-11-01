# SPDX-License-Identifier: GPL-3.0-or-later
"""The Campfire: the first effect, created from F3 search."""

import bpy

from ..core import bounces, view_sync
from . import fire_light, flame_material, plane_stack

CAMPFIRE = {"Sites": 7, "Layers": 4, "Spread": 0.42, "Spacing": 0.05,
            "Width": 1.05, "Height": 1.9, "Seed": 3}
CAMPFIRE_LIGHT = {"energy": 90.0, "radius": 0.3}


def create_campfire(context, location):
    scene = context.scene
    material = flame_material.build_flame_material("FAS_Flame")
    glow = flame_material.build_glow_material("FAS_Glow")
    tree = plane_stack.build_tree("FAS_Campfire", material, glow)

    obj = bpy.data.objects.new("Campfire", bpy.data.meshes.new("Campfire"))
    obj.location = location
    scene.collection.objects.link(obj)
    modifier = obj.modifiers.new("Fire", "NODES")
    modifier.node_group = tree
    plane_stack.set_inputs(modifier, {**CAMPFIRE, "Face Viewport": True,
                                      "View Target": view_sync.ensure_target(scene)})
    plane_stack.hide_from_lighting(obj)

    light, _action = fire_light.build_light("Campfire Light", **CAMPFIRE_LIGHT)
    scene.collection.objects.link(light)
    light.parent = obj
    light.location = (0.0, 0.0, CAMPFIRE["Height"] * 0.4)

    bounces.raise_for(scene, CAMPFIRE["Sites"] * CAMPFIRE["Layers"] + 1)  # + the glow card
    return obj


class FAS_OT_campfire_create(bpy.types.Operator):
    bl_idname = "fas.campfire_create"
    bl_label = "Add Campfire"
    bl_description = "Add a Campfire at the 3D cursor"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        create_campfire(context, context.scene.cursor.location)
        if context.scene.camera is None:
            self.report({"WARNING"}, "This scene has no camera: add one before rendering")
        return {"FINISHED"}


CLASSES = (FAS_OT_campfire_create,)
