# SPDX-License-Identifier: GPL-3.0-or-later
"""The Campfire: the first effect, created from F3 search."""

import bpy

from .. import constants as C
from ..core import delete
from . import creation, flame_material

CAMPFIRE = {"Sites": 7, "Layers": 4, "Spread": 0.42, "Spacing": 0.05,
            "Width": 1.05, "Height": 1.9, "Seed": 3}
CAMPFIRE_LIGHT = {"energy": 90.0, "radius": 0.3}


def create_campfire(context, location):
    return creation.create_plane_effect(
        context, C.KIND_FIRE, "Campfire",
        flame_material.build_flame_material("FAS_Flame"), CAMPFIRE, location,
        glow=flame_material.build_glow_material("FAS_Glow"), light=dict(CAMPFIRE_LIGHT))


class FAS_OT_campfire_create(bpy.types.Operator):
    bl_idname = "fas.campfire_create"
    bl_label = "Add Campfire"
    bl_description = "Add a Campfire at the 3D cursor"
    bl_options = {"REGISTER", "UNDO"}

    @delete.guarded_create
    def execute(self, context):
        create_campfire(context, context.scene.cursor.location)
        if context.scene.camera is None:
            self.report({"WARNING"}, "This scene has no camera: add one before rendering")
        return {"FINISHED"}


CLASSES = (FAS_OT_campfire_create,)
