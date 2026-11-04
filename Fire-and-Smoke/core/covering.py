# SPDX-License-Identifier: GPL-3.0-or-later
"""The buyer's meshes that hide a fire: a fire made at the 3D cursor often lands inside
the default cube, which hides its flames in every view.

A mesh counts when a point in the fire's flames lies inside its bounding box: the
fire's light and its origin, and a simulated fire's emitter.  Only visible, solid meshes
of the buyer's count.  Flat planes never do, since a point on one isn't inside it, and
the add-on never moves or hides them: it says which are in the way.
"""

from mathutils import Vector

from .. import constants as C

FIRE_KINDS = (C.KIND_FIRE, C.KIND_SIM_FIRE)
MAX_CHECKED = 500      # objects checked while drawing the panel; Create checks them all
MARGIN = 1e-4


def _points(entry):
    points = []
    for obj in (entry.light, entry.primary, entry.emitter if entry.kind == C.KIND_SIM_FIRE else None):
        if obj is not None:
            points.append(obj.matrix_world.translation.copy())
    return points


def _solid_mesh(obj, entry):
    if obj.type != "MESH" or C.OWNER_PROP in obj.keys() or obj == entry.source:
        return False
    if obj.display_type in {"WIRE", "BOUNDS"} or not obj.visible_get():
        return False
    # A fluid domain of the buyer's shows its simulation, not its box.
    return not any(m.type == "FLUID" and m.fluid_type == "DOMAIN" for m in obj.modifiers)


def _inside(obj, point):
    corners = [Vector(c) for c in obj.bound_box]
    try:
        local = obj.matrix_world.inverted() @ point
    except ValueError:      # a zero scale can't be inverted
        return False
    low = Vector(min(c[i] for c in corners) for i in range(3))
    high = Vector(max(c[i] for c in corners) for i in range(3))
    return all(low[i] + MARGIN < local[i] < high[i] - MARGIN for i in range(3))


def covering(scene, entry, limit=None):
    """Names of the buyer's meshes that hide this fire, or [] (also for non-fires)."""
    if entry.kind not in FIRE_KINDS or entry.primary is None:
        return []
    objects = list(scene.objects)
    if limit is not None and len(objects) > limit:
        return []
    points = _points(entry)
    return [obj.name for obj in objects
            if _solid_mesh(obj, entry) and any(_inside(obj, p) for p in points)]


def sentence(names):
    """The plain message for the buyer."""
    if not names:
        return ""
    if len(names) == 1:
        return f"{names[0]} is in the way and hides the fire: hide or move it"
    if len(names) > 3:
        listed = f"{', '.join(names[:3])} and {len(names) - 3} more"
    else:
        listed = f"{', '.join(names[:-1])} and {names[-1]}"
    return f"{listed} are in the way and hide the fire: hide or move them"
