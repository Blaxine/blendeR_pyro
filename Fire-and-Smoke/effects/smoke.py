# SPDX-License-Identifier: GPL-3.0-or-later
"""Smoke on a point and smoke columns."""

import bpy

from .. import constants as C
from ..core import delete
from . import creation, smoke_material

SMOKE = {"Sites": 3, "Layers": 5, "Spread": 0.14, "Spacing": 0.09,
         "Width": 2.8, "Height": 4.4, "Seed": 5}
SMOKE_LOOK = {"dark": (0.09, 0.09, 0.10, 1.0), "light": (0.42, 0.42, 0.44, 1.0),
              "density": 0.26, "speed": 0.42, "scale": 2.4, "aspect": 1.6}

COLUMN = {"Sites": 5, "Layers": 6, "Spread": 0.45, "Spacing": 0.16,
          "Width": 7.0, "Height": 12.0, "Seed": 8}
COLUMN_LOOK = {"dark": (0.006, 0.006, 0.007, 1.0), "light": (0.055, 0.055, 0.06, 1.0),
               "density": 0.55, "speed": 0.3, "scale": 2.6, "base_width": 0.07, "top_width": 0.5, "aspect": 1.7}


def create_smoke(context, location, kind=C.KIND_SMOKE, name="Smoke", stack=SMOKE, look=SMOKE_LOOK):
    return creation.create_plane_effect(
        context, kind, name, smoke_material.build_smoke_material(f"FAS_{name}", **look),
        stack, location)


class FAS_OT_smoke_create(bpy.types.Operator):
    bl_idname = "fas.smoke_create"
    bl_label = "Add Smoke"
    bl_description = "Add smoke at the 3D cursor"
    bl_options = {"REGISTER", "UNDO"}

    @delete.guarded_create
    def execute(self, context):
        create_smoke(context, context.scene.cursor.location)
        return {"FINISHED"}


class FAS_OT_column_create(bpy.types.Operator):
    bl_idname = "fas.column_create"
    bl_label = "Add Smoke Column"
    bl_description = "Add a tall smoke column at the 3D cursor"
    bl_options = {"REGISTER", "UNDO"}

    @delete.guarded_create
    def execute(self, context):
        create_smoke(context, context.scene.cursor.location, C.KIND_COLUMN, "Smoke Column",
                     COLUMN, COLUMN_LOOK)
        return {"FINISHED"}


CLASSES = (FAS_OT_smoke_create, FAS_OT_column_create)
