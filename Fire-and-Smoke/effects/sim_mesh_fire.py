# SPDX-License-Identifier: GPL-3.0-or-later
"""Fire and Smoke from Mesh: a Simulated Fire that burns from the buyer's own mesh.

The buyer's mesh is never changed: no modifier, constraint, tag or vertex group.  The
emitter is the effect's own object with an empty mesh.  Its Geometry Nodes modifier
outputs the buyer's evaluated mesh through Object Info in Relative space, so the fire
follows the mesh as it's edited, deformed or moved, and its Fluid flow emits from that
surface.  The domain is sized around the mesh once, at Create, and follows it with
Copy Location.  The emitter and the fire light are the domain's children: Delete
keeps an owned object that isn't.
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
    return sim_fire.record(context, kind, effect_uuid, domain, emitter, light, collection, preset,
                           source=source)
