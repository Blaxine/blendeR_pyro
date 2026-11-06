# SPDX-License-Identifier: GPL-3.0-or-later
"""Fire and Smoke from Mesh: a Simulated Fire that burns from the buyer's own mesh.

The buyer's mesh is never changed: no modifier, constraint, tag or vertex group.  The
emitter is the effect's own object with an empty mesh.  Its Geometry Nodes modifier
outputs the buyer's evaluated mesh through Object Info in Relative space, so the fire
follows the mesh as it's edited, deformed or moved, and its Fluid flow emits from that
surface.  The domain is sized around the mesh once, at Create, and follows it with
Copy Location.  The emitter and the fire light are the domain's children: Delete
keeps an owned object that isn't.

Burn From is stored as a group name, never a position.  The Fluid flow's vertex group
is a name on the emitter's own list, but Blender keeps it as a position and reads that
position in the evaluated mesh's weights, which come from the buyer's mesh in the
buyer's order.  So the emitter's list always mirrors the buyer's group names, in their
order, and the flow's group is set again by name after every sync.

While the chosen group or the mesh is gone, the flow's Fluid modifier is muted, so the
fire stops rather than burning somewhere the buyer didn't choose.
"""

import bpy
from mathutils import Vector

from .. import constants as C
from ..core import naming
from . import mesh_fire, plane_stack, sim_fire, sim_presets

SOURCE_INPUT = "Source"
# Room around the mesh, in multiples of its largest size: beside it for the flames to
# spread and sway, above it for them to rise, and a little below it.
SIDE_ROOM = 0.6
HEADROOM = 3.0
FLOOR_ROOM = 0.05
LIGHT_ABOVE = 0.6
SMALLEST = 0.01

WHOLE_MESH = "FAS_WHOLE_MESH"
WHOLE_MESH_LABEL = "Whole Mesh"
MISSING = 1 << 20
# Blender's enum API keeps pointers to the item strings: hold each entry's last list.
_items_kept = {}


def world_bounds(obj):
    """The lowest and highest corners of the object's bounding box, in the world."""
    corners = [obj.matrix_world @ Vector(corner) for corner in obj.bound_box]
    low = Vector([min(c[i] for c in corners) for i in range(3)])
    high = Vector([max(c[i] for c in corners) for i in range(3)])
    return low, high


def _copy_tree(name, kind, effect_uuid):
    """A modifier tree that outputs the Source object's evaluated mesh where it is."""
    tree = naming.tag(bpy.data.node_groups.new(name, "GeometryNodeTree"), kind, effect_uuid)
    tree.is_modifier = True
    tree.interface.new_socket("Geometry", in_out="OUTPUT", socket_type="NodeSocketGeometry")
    tree.interface.new_socket(SOURCE_INPUT, in_out="INPUT", socket_type="NodeSocketObject",
                              description="The mesh that burns. It's read, never changed")
    group_in = tree.nodes.new("NodeGroupInput")
    group_in.location = (-400.0, 0.0)
    info = tree.nodes.new("GeometryNodeObjectInfo")
    info.transform_space = "RELATIVE"
    info.location = (-150.0, 0.0)
    group_out = tree.nodes.new("NodeGroupOutput")
    group_out.location = (150.0, 0.0)
    tree.links.new(group_in.outputs[SOURCE_INPUT], info.inputs["Object"])
    tree.links.new(info.outputs["Geometry"], group_out.inputs["Geometry"])
    return tree


def group_names(obj):
    return [group.name for group in obj.vertex_groups] if obj is not None else []


def burn_from_items(entry, _context=None):
    """Whole Mesh, then the mesh's groups in its order, then a chosen group that's gone."""
    names = group_names(entry.source)
    items = [(WHOLE_MESH, WHOLE_MESH_LABEL, "Fire comes from all of the mesh", "MESH_DATA", 0)]
    for index, group in enumerate(names):
        items.append((group, group, f"Fire comes only from the {group} vertex group, as strongly as "
                                    "its painted weights", "GROUP_VERTEX", index + 1))
    if entry.burn_from and entry.burn_from not in names:
        items.append((entry.burn_from, f"{entry.burn_from} (missing)",
                      "This vertex group isn't on the mesh any more", "ERROR", MISSING))
    _items_kept[entry.as_pointer()] = items
    return items


def burn_from_get(entry):
    if not entry.burn_from:
        return 0
    names = group_names(entry.source)
    return names.index(entry.burn_from) + 1 if entry.burn_from in names else MISSING


def burn_from_set(entry, value):
    if value == 0:
        entry.burn_from = ""
        return
    names = group_names(entry.source)
    if 0 < value <= len(names):
        entry.burn_from = names[value - 1]


def missing_group(entry):
    """The chosen group's name while the mesh no longer has it, or None."""
    if entry.kind != C.KIND_SIM_MESH_FIRE or not entry.burn_from or entry.source is None:
        return None
    return None if entry.burn_from in group_names(entry.source) else entry.burn_from


def can_burn(entry):
    return entry.source is not None and missing_group(entry) is None


def _set_burning(entry, burning):
    """Mute or unmute the flow, in the viewport and renders.  True if it changed."""
    modifier = sim_fire.find_modifier(entry.emitter, "FLOW")
    if modifier is None or (modifier.show_viewport == burning and modifier.show_render == burning):
        return False
    modifier.show_viewport = burning
    modifier.show_render = burning
    return True


def sync(entry):
    """Mirror the mesh's group names on the emitter, in order, point the flow at the
    chosen group by name, and stop the flow while the group or mesh is gone.  Writes
    only what differs.  True if the fire it makes changed, so it must simulate again."""
    source, emitter = entry.source, entry.emitter
    if emitter is None:
        return False
    changed = False
    names = group_names(source)
    if source is not None and group_names(emitter) != names:
        emitter.vertex_groups.clear()
        for group in names:
            emitter.vertex_groups.new(name=group)
        # 4.5 can keep the copy's weights in the old order after a group is removed from
        # Python: re-evaluate both.  A tag only refreshes the mesh, never changes it.
        source.update_tag(refresh={"DATA"})
        emitter.update_tag(refresh={"DATA"})
        # Positions moved: only fire from a group depends on them.
        changed = bool(entry.burn_from)
    flow = sim_fire.flow_settings(entry)
    if flow is not None:
        wanted = entry.burn_from if entry.burn_from in names else ""
        if flow.density_vertex_group != wanted:
            flow.density_vertex_group = wanted
            changed = True
    if _set_burning(entry, can_burn(entry)):
        changed = True
    return changed


def watch(scene):
    """The mesh or its group list changed: mirror it again, and simulate again if the
    fire changed, in case anything was played before the sync."""
    for entry in getattr(scene, "fas_effects", ()):
        if entry.kind == C.KIND_SIM_MESH_FIRE and sync(entry):
            sim_fire.clear_cache(entry)


def dense_warning(source):
    if source is not None and source.type == "MESH" and len(source.data.polygons) > mesh_fire.WARN_FACES:
        return "This mesh is dense, so the fire will be slower to simulate"
    return None


def create_sim_mesh_fire(context, source, preset=sim_presets.DEFAULT):
    """Build the fire around the buyer's mesh, then apply the preset, as Apply does."""
    if not bpy.app.build_options.fluid:
        raise RuntimeError(sim_fire.NO_FLUID)
    problem = mesh_fire.source_problem(source)
    if problem:
        raise RuntimeError(problem)
    if preset not in sim_presets.CATALOG:
        raise RuntimeError(sim_presets.CHOOSE)
    package = sim_presets.CATALOG[preset]
    scene = context.scene
    kind = C.KIND_SIM_MESH_FIRE
    effect_uuid = naming.new_uuid()
    name = f"{source.name} Fire"
    collection = naming.new_effect_collection(scene, kind, effect_uuid, name)

    low, high = world_bounds(source)
    size = max(max(high - low), SMALLEST)
    centre = (low + high) * 0.5
    bottom = low.z - FLOOR_ROOM * size
    height = high.z + HEADROOM * size - bottom
    box = (high.x - low.x + 2.0 * SIDE_ROOM * size, high.y - low.y + 2.0 * SIDE_ROOM * size, height)

    domain_mesh = naming.tag(sim_fire.fill_box(bpy.data.meshes.new(f"{name} Domain"), box, height * 0.5),
                             kind, effect_uuid)
    domain_mesh.materials.append(naming.tag(sim_fire._volume_material(f"FAS_{name}"), kind, effect_uuid))
    domain = naming.tag(bpy.data.objects.new(name, domain_mesh), kind, effect_uuid)
    collection.objects.link(domain)
    # It follows the mesh's moves, never its rotation or scale: fire rises in the world.
    follow = domain.constraints.new("COPY_LOCATION")
    follow.target = source
    follow.use_offset = True
    domain.location = Vector((centre.x, centre.y, bottom)) - source.matrix_world.translation

    emitter_mesh = naming.tag(bpy.data.meshes.new(f"{name} Emitter"), kind, effect_uuid)
    emitter = naming.tag(bpy.data.objects.new(f"{name} Emitter", emitter_mesh), kind, effect_uuid)
    collection.objects.link(emitter)
    emitter.parent = domain
    emitter.display_type = "WIRE"
    emitter.hide_render = True
    copy = emitter.modifiers.new("Mesh Copy", "NODES")
    copy.node_group = _copy_tree(f"FAS_{name} Copy", kind, effect_uuid)
    plane_stack.set_inputs(copy, {SOURCE_INPUT: source})
    sim_fire.add_flow(emitter)

    sim_fire.add_domain(scene, domain, collection, effect_uuid, package["entry"]["detail"])
    light = sim_fire.add_light(collection, domain, kind, effect_uuid, f"{name} Light", package["light"],
                               (0.0, 0.0, high.z - bottom + LIGHT_ABOVE * size))
    effect_uuid = sim_fire.record(context, kind, effect_uuid, domain, emitter, light, collection, preset,
                                  source=source)
    entry = next(e for e in scene.fas_effects if e.uuid == effect_uuid)
    sync(entry)
    return effect_uuid
