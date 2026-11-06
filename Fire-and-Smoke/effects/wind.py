# SPDX-License-Identifier: GPL-3.0-or-later
"""Wind: a Blender Wind force field, owned like every other effect.

It blows the Simulated Fire's flames and smoke and the embers.  The plane fires and
smoke are animated noise, not simulations, so wind doesn't move them.

Blender's wind strength is far too strong for a fire: at 1 a campfire's flames lie flat
and run into the edge of its box.  Power 1 is strength 0.25, a strong breeze, so the
slider's range stays useful (docs/LOOK_TEST.md).  The field is a Plane, which blows the
same way everywhere in front of it, so it's kept upwind of where it was made and turned
to face the way it blows.
"""

import math

import bpy

from .. import constants as C
from ..core import delete, naming, registry

NAME = "Wind"
STRENGTH_PER_POWER = 0.25
NOISE_PER_GUST = 2.0
UPWIND = 3.0            # metres from the 3D cursor, against the wind
HEIGHT = 1.0
DEFAULT_POWER = 0.4     # a light breeze: strength 0.1
DEFAULT_GUSTS = 0.3
NOTE = "Wind blows the Simulated Fire and embers. The plane fires and smoke don't move with it"


def field(entry):
    obj = entry.primary
    return obj.field if obj is not None and obj.field is not None and obj.field.type == "WIND" else None


def place(entry):
    """Upwind of the spot the wind was made for, facing the way it blows."""
    obj = entry.primary
    if obj is None:
        return
    angle = entry.wind_direction
    centre = entry.wind_centre
    obj.location = (centre[0] - UPWIND * math.cos(angle), centre[1] - UPWIND * math.sin(angle), centre[2] + HEIGHT)
    # A field blows along its local Z: lay Z down along the direction.
    obj.rotation_euler = (0.0, math.radians(90.0), angle)


def apply(entry):
    settings = field(entry)
    if settings is None:
        return
    settings.strength = entry.wind_power * STRENGTH_PER_POWER
    settings.noise = entry.wind_gusts * NOISE_PER_GUST


def simulations_changed(scene):
    """Wind isn't a setting a Replay cache notices: clear every simulated fire so the
    next play from the first frame shows it."""
    from . import sim_fire
    for entry in scene.fas_effects:
        if entry.kind in C.SIM_KINDS and entry.primary is not None:
            sim_fire.clear_cache(entry)


def create_wind(context, location):
    scene = context.scene
    kind = C.KIND_WIND
    effect_uuid = naming.new_uuid()
    collection = naming.new_effect_collection(scene, kind, effect_uuid, NAME)
    obj = naming.tag(bpy.data.objects.new(NAME, None), kind, effect_uuid)
    obj.empty_display_type = "SINGLE_ARROW"
    obj.empty_display_size = 1.0
    collection.objects.link(obj)
    # A new object has no force field settings, and only this operator makes them.
    # The override points it at the wind alone: the buyer's selection doesn't change.
    with context.temp_override(object=obj, active_object=obj, selected_objects=[obj]):
        bpy.ops.object.forcefield_toggle()
    obj.field.type = "WIND"
    obj.field.shape = "PLANE"
    obj.field.flow = 0.0

    entry = registry.add(scene, kind, effect_uuid, primary=obj, root_collection=collection)
    entry.planes = 0
    entry.wind_centre = location
    # Through the entry, so the sliders and the field always agree.
    entry.wind_power = DEFAULT_POWER
    entry.wind_gusts = DEFAULT_GUSTS
    entry.wind_direction = 0.0
    place(entry)
    apply(entry)
    simulations_changed(scene)
    return effect_uuid


class FAS_OT_wind_create(bpy.types.Operator):
    bl_idname = "fas.wind_create"
    bl_label = "Add Wind"
    bl_description = ("Add wind that blows the Simulated Fire and embers. "
                      "Set its power and direction in its box")
    bl_options = {"REGISTER", "UNDO"}

    @delete.guarded_create
    def execute(self, context):
        create_wind(context, context.scene.cursor.location.copy())
        self.report({"INFO"}, "Wind added: press play from the first frame to see it blow the fire")
        return {"FINISHED"}


CLASSES = (FAS_OT_wind_create,)
