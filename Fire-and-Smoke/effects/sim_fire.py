# SPDX-License-Identifier: GPL-3.0-or-later
"""Simulated Fire: a real Mantaflow fire, built by the add-on itself.

The domain is the effect's primary, built at full size with an object scale of 1, and
the emitter is its child.  The domain takes flows and effectors only from the effect's
own collection, and its Replay cache simulates forward as the timeline plays: there's
no bake step.  Replay only adds frames in order, so a jump past the last simulated
frame holds the last state until the buyer plays from the first frame again.

Create builds the effect's structure, then applies one of ``sim_presets`` onto it:
Normal Fire, Candle Fire or Campfire.  The structure followed Blender's Quick Smoke,
which the add-on never calls: it changes the buyer's selection and makes untagged
objects.  The look values live in the presets.
"""

import math

import bpy

from .. import constants as C
from ..core import bounces, cache_folder, naming, registry
from . import fire_light, light_mode, sim_presets

NO_FLUID = "This Blender was built without Fluid, so it can't make a Simulated Fire"
NO_FLUID_HERE = "This Blender was built without Fluid, so this fire can't simulate"

# The flame's colour by how much is burning: a pale core, then orange, then deep red
# at the tips, as a real campfire shades.  A preset sets how bright it is; at 0 the
# flame shows only its blackbody glow.
FLAME_RAMP = ((0.0, (0.0, 0.0, 0.0)), (0.12, (0.35, 0.03, 0.0)), (0.35, (1.0, 0.18, 0.01)),
              (0.65, (1.0, 0.42, 0.05)), (1.0, (1.0, 0.72, 0.3)))
RAMP_NODE = "fas_flame_colour"
STRENGTH_NODE = "fas_flame_strength"


def _fill(mesh, verts, faces):
    """Replace a mesh's geometry in place: its materials and ownership tag stay."""
    mesh.clear_geometry()
    mesh.from_pydata(verts, [], faces)
    mesh.update()
    return mesh


def fill_box(mesh, size, centre_z):
    x, y, z = (s * 0.5 for s in size)
    lo, hi = centre_z - z, centre_z + z
    verts = [(-x, -y, lo), (x, -y, lo), (x, y, lo), (-x, y, lo),
             (-x, -y, hi), (x, -y, hi), (x, y, hi), (-x, y, hi)]
    faces = [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]
    return _fill(mesh, verts, faces)


def _disc(verts, faces, x, y, z, radius, sides):
    base = len(verts)
    verts.append((x, y, z))
    verts += [(x + radius * math.cos(2 * math.pi * i / sides), y + radius * math.sin(2 * math.pi * i / sides), z)
              for i in range(sides)]
    faces += [(base, base + 1 + i, base + 1 + (i + 1) % sides) for i in range(sides)]


def fill_disc(mesh, radius, sides=24):
    verts, faces = [], []
    _disc(verts, faces, 0.0, 0.0, 0.0, radius, sides)
    return _fill(mesh, verts, faces)


def fill_patches(mesh, patches, sides=12):
    """Several small discs at different heights, like flames rising from separate logs:
    each one gives its own tongue of flame, where one disc gives one smooth column."""
    verts, faces = [], []
    for x, y, z, radius in patches:
        _disc(verts, faces, x, y, z, radius, sides)
    return _fill(mesh, verts, faces)


def flame_colour(entry):
    """The flame colour nodes, (ramp, strength).  A fire from an older file gets them added."""
    node = volume_node(entry)
    if node is None:
        return None, None
    tree = node.id_data
    ramp, strength = tree.nodes.get(RAMP_NODE), tree.nodes.get(STRENGTH_NODE)
    if ramp is None or strength is None:
        ramp, strength = _add_flame_colour(tree, node)
    return ramp, strength


def _add_flame_colour(tree, volume):
    info = tree.nodes.new("ShaderNodeVolumeInfo")
    info.location = (-600.0, 0.0)
    ramp = tree.nodes.new("ShaderNodeValToRGB")
    ramp.name = RAMP_NODE
    ramp.location = (-350.0, 100.0)
    elements = ramp.color_ramp.elements
    while len(elements) < len(FLAME_RAMP):
        elements.new(0.5)
    for element, (position, colour) in zip(elements, FLAME_RAMP):
        element.position = position
        element.color = (*colour, 1.0)
    strength = tree.nodes.new("ShaderNodeMath")
    strength.name = STRENGTH_NODE
    strength.operation = "MULTIPLY"
    strength.location = (-350.0, -150.0)
    strength.inputs[1].default_value = 0.0
    tree.links.new(info.outputs["Flame"], ramp.inputs["Fac"])
    tree.links.new(info.outputs["Flame"], strength.inputs[0])
    tree.links.new(ramp.outputs["Color"], volume.inputs["Emission Color"])
    tree.links.new(strength.outputs["Value"], volume.inputs["Emission Strength"])
    return ramp, strength


def _volume_material(name):
    """The values are the preset's: ``sim_presets.apply`` writes them."""
    material = bpy.data.materials.new(name)
    material.use_nodes = True
    material.diffuse_color = (1.0, 0.35, 0.05, 1.0)  # what Solid view shows
    tree = material.node_tree
    tree.nodes.clear()
    volume = tree.nodes.new("ShaderNodeVolumePrincipled")
    volume.name = "fas_volume"
    output = tree.nodes.new("ShaderNodeOutputMaterial")
    output.location = (300.0, 0.0)
    tree.links.new(volume.outputs["Volume"], output.inputs["Volume"])
    _add_flame_colour(tree, volume)
    return material


def find_modifier(obj, fluid_type):
    if obj is None:
        return None
    return next((m for m in obj.modifiers if m.type == "FLUID" and m.fluid_type == fluid_type), None)


def domain_settings(entry):
    return cache_folder.domain_settings(entry.primary)


def flow_settings(entry):
    modifier = find_modifier(entry.emitter, "FLOW")
    return modifier.flow_settings if modifier is not None else None


def volume_node(entry):
    primary = entry.primary
    if primary is None or primary.data is None:
        return None
    for material in primary.data.materials:
        if material is not None and material.node_tree is not None:
            node = material.node_tree.nodes.get("fas_volume")
            if node is not None:
                return node
    return None


def clear_cache(entry):
    """Make the next play from the first frame simulate again.

    A Python change to a simulation setting isn't relied on to clear the Replay cache.
    Reassigning the cache type to its own value does, on 4.5 and 5.2; reassigning
    ``cache_frame_end`` doesn't."""
    settings = domain_settings(entry)
    if settings is not None:
        settings.cache_type = settings.cache_type


def set_range(settings, start, end):
    """Each bound is clamped by the other, so widen before narrowing."""
    if start > settings.cache_frame_end:
        settings.cache_frame_end = end
        settings.cache_frame_start = start
    else:
        settings.cache_frame_start = start
        settings.cache_frame_end = end


def create_sim_fire(context, location, preset=sim_presets.DEFAULT):
    """Build the structure, then apply the preset onto it, the same way Apply does."""
    if not bpy.app.build_options.fluid:
        raise RuntimeError(NO_FLUID)
    if preset not in sim_presets.CATALOG:
        raise RuntimeError(sim_presets.CHOOSE)
    package = sim_presets.CATALOG[preset]
    shape, name = package["shape"], package["name"]
    scene = context.scene
    kind = C.KIND_SIM_FIRE
    effect_uuid = naming.new_uuid()
    collection = naming.new_effect_collection(scene, kind, effect_uuid, name)

    domain_mesh = naming.tag(fill_box(bpy.data.meshes.new(f"{name} Domain"), shape["domain_size"],
                                      shape["domain_centre_z"]), kind, effect_uuid)
    material = naming.tag(_volume_material(f"FAS_{name}"), kind, effect_uuid)
    domain_mesh.materials.append(material)
    domain = naming.tag(bpy.data.objects.new(name, domain_mesh), kind, effect_uuid)
    domain.location = location
    collection.objects.link(domain)

    emitter_mesh = naming.tag(bpy.data.meshes.new(f"{name} Emitter"), kind, effect_uuid)
    if shape["emitter_patches"]:
        fill_patches(emitter_mesh, shape["emitter_patches"])
    else:
        fill_disc(emitter_mesh, shape["emitter_radius"])
    emitter = naming.tag(bpy.data.objects.new(f"{name} Emitter", emitter_mesh), kind, effect_uuid)
    collection.objects.link(emitter)
    emitter.parent = domain
    emitter.location = (0.0, 0.0, shape["emitter_z"])
    emitter.display_type = "WIRE"
    emitter.hide_render = True

    flow = emitter.modifiers.new("Fluid", "FLUID")
    flow.fluid_type = "FLOW"
    emission = flow.flow_settings
    emission.flow_type = "BOTH"
    emission.flow_behavior = "INFLOW"
    emission.surface_distance = 1.0

    fluid = domain.modifiers.new("Fluid", "FLUID")
    fluid.fluid_type = "DOMAIN"
    settings = fluid.domain_settings
    settings.domain_type = "GAS"
    settings.cfl_condition = 4.0
    settings.use_noise = False
    if bpy.app.build_options.openvdb:
        settings.cache_data_format = "OPENVDB"
    settings.cache_type = "REPLAY"
    settings.resolution_max = package["entry"]["detail"]
    settings.fluid_group = collection
    settings.effector_group = collection
    set_range(settings, scene.frame_start, scene.frame_end)
    settings.cache_directory = cache_folder.path_for(effect_uuid)

    values = package["light"]
    light, action = fire_light.build_light(f"{name} Light", values["energy"], radius=values["radius"],
                                           flicker=values["flicker"], speed=values["speed"])
    for id_block in (light, light.data, action):
        naming.tag(id_block, kind, effect_uuid)
    collection.objects.link(light)
    light.parent = domain
    light.location = (0.0, 0.0, shape["light_height"])

    entry = registry.add(scene, kind, effect_uuid, primary=domain, root_collection=collection)
    entry.emitter = emitter
    entry.planes = 0
    entry.light = light
    light_mode.apply(domain, light, light_mode.REAL)
    entry.light_mode = light_mode.REAL
    sim_presets.apply(context, entry, preset)
    bounces.after_create(scene)
    return effect_uuid
