# SPDX-License-Identifier: GPL-3.0-or-later
"""Fire on a mesh: a separate object that reads the buyer's mesh and follows it.

The buyer's object is never changed: no modifier, no tag, no data.  The fire's own
light follows it through a constraint that lives on the light.
"""

import math

import bpy
from mathutils import Vector

from .. import constants as C
from ..core import delete
from . import creation, flame_material

MIN_SITES = 12
MAX_SITES = 120
SITES_PER_SQUARE_METRE = 1.8
LAYERS = 2
# The fire rebuilds on every frame: measured at about 15 ms per frame at a million
# faces, against 41 ms per frame at 24 fps, before the source's own cost.
MAX_FACES = 2_000_000
WARN_FACES = 500_000


def surface_area(obj):
    """The object's surface in square metres, with its scale applied."""
    mesh = obj.data
    scale = obj.matrix_world.to_scale()
    if not mesh.polygons:
        return 0.0
    uniform = abs(scale.x * scale.y * scale.z) ** (2.0 / 3.0)
    return sum(p.area for p in mesh.polygons) * uniform


def _light_offset(obj):
    """Above the object's top, from its origin: inside a closed mesh a light lights nothing."""
    corners = [obj.matrix_world @ Vector(corner) for corner in obj.bound_box]
    centre = sum(corners, Vector()) / 8.0
    top = max(corner.z for corner in corners)
    above = top + max(obj.dimensions) * 0.6
    return Vector((centre.x, centre.y, above)) - obj.matrix_world.translation


def source_problem(obj):
    """Why this object can't burn, as a sentence for the buyer, or None."""
    if obj is None or obj.type != "MESH":
        return "Select a mesh first: the fire needs something to burn"
    if obj.get(C.OWNER_PROP):
        return "That object is part of an effect: select one of your own meshes"
    if not obj.data.polygons:
        return "That mesh has no faces to burn"
    if len(obj.data.polygons) > MAX_FACES:
        return (f"That mesh has {len(obj.data.polygons):,} faces, over the limit of {MAX_FACES:,}: "
                "use a simpler copy for the fire")
    return None


def is_missing_source(entry):
    return entry.kind == C.KIND_MESH_FIRE and entry.source is None


def create_mesh_fire(context, source):
    problem = source_problem(source)
    if problem:
        raise RuntimeError(problem)
    area = surface_area(source)
    sites = max(MIN_SITES, min(MAX_SITES, int(area * SITES_PER_SQUARE_METRE)))
    gap = math.sqrt(area / sites)
    stack = {"Sites": sites, "Layers": LAYERS, "Spread": 0.0, "Spacing": gap * 0.1,
             "Width": gap * 1.5, "Height": gap * 1.9, "Seed": 2}
    light = {"energy": min(60.0 + area * 14.0, 800.0), "radius": max(gap * 2.0, 0.2),
             "height": 0.0}
    material = flame_material.build_flame_material(
        "FAS_Flame", speed=1.5, strength=0.7, steep_floor=0.3)
    effect_uuid = creation.create_plane_effect(
        context, C.KIND_MESH_FIRE, "Mesh Fire", material, stack, (0.0, 0.0, 0.0), light=light,
        source=source, density=sites / area)
    entry = next(e for e in context.scene.fas_effects if e.uuid == effect_uuid)
    constraint = entry.light.constraints.new("COPY_LOCATION")
    constraint.target = source
    entry.light.parent = entry.primary
    entry.light.location = (0.0, 0.0, 0.0)
    constraint.use_offset = True
    entry.light.location = _light_offset(source)
    return effect_uuid


class FAS_OT_mesh_fire_create(bpy.types.Operator):
    bl_idname = "fas.mesh_fire_create"
    bl_label = "Set Mesh on Fire"
    bl_description = "Set the selected mesh on fire, without changing it"
    bl_options = {"REGISTER", "UNDO"}

    @delete.guarded_create
    def execute(self, context):
        source = context.active_object
        create_mesh_fire(context, source)
        if len(source.data.polygons) > WARN_FACES:
            self.report({"WARNING"}, "This mesh is dense, so scrubbing may be slower")
        return {"FINISHED"}


CLASSES = (FAS_OT_mesh_fire_create,)
