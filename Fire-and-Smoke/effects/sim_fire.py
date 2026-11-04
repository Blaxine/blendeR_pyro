# SPDX-License-Identifier: GPL-3.0-or-later
"""Simulated Campfire: a real Mantaflow fire, built by the add-on itself.

The domain is the effect's primary, built at full size with an object scale of 1, and
the emitter is its child.  The domain takes flows and effectors only from the effect's
own collection, and its Replay cache simulates forward as the timeline plays: there's
no bake step.  Replay only adds frames in order, so a jump past the last simulated
frame holds the last state until the buyer plays from the first frame again.

The starting values followed Blender's Quick Smoke, which the add-on never calls: it
changes the buyer's selection and makes untagged objects.  The look values below were
tuned in Cycles from there (``docs/LOOK_TEST.md``): some vorticity breaks the smooth
column up, the flame burns out lower, and dark, thinner smoke rises above it instead
of the whole plume glowing in the fire light.
"""

import math

import bpy

from .. import constants as C
from ..core import bounces, cache_folder, naming, registry
from . import fire_light, light_mode

NO_FLUID = "This Blender was built without Fluid, so it can't make a Simulated Campfire"
NO_FLUID_HERE = "This Blender was built without Fluid, so this fire can't simulate"

EMITTER_RADIUS = 0.35
EMITTER_Z = 0.05
DOMAIN_SIZE = (1.4, 1.4, 2.6)
DOMAIN_CENTRE_Z = 1.25
RESOLUTION = 64
VORTICITY = 0.2
BURNING_RATE = 1.1
VOLUME_DENSITY = 3.0
SMOKE_COLOUR = 0.05
BLACKBODY = 1.0
LIGHT = {"energy": 45.0, "radius": 0.3}
LIGHT_HEIGHT = 0.5


def _box_mesh(name, size, centre_z):
    x, y, z = (s * 0.5 for s in size)
    lo, hi = centre_z - z, centre_z + z
    verts = [(-x, -y, lo), (x, -y, lo), (x, y, lo), (-x, y, lo),
             (-x, -y, hi), (x, -y, hi), (x, y, hi), (-x, y, hi)]
    faces = [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(verts, [], faces)
    mesh.update()
    return mesh


def _disc_mesh(name, radius, z, sides=24):
    verts = [(0.0, 0.0, z)] + [(radius * math.cos(2 * math.pi * i / sides),
                                radius * math.sin(2 * math.pi * i / sides), z) for i in range(sides)]
    faces = [(0, 1 + i, 1 + (i + 1) % sides) for i in range(sides)]
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(verts, [], faces)
    mesh.update()
    return mesh


def _volume_material(name):
    material = bpy.data.materials.new(name)
    material.use_nodes = True
    material.diffuse_color = (1.0, 0.35, 0.05, 1.0)  # what Solid view shows
    tree = material.node_tree
    tree.nodes.clear()
    volume = tree.nodes.new("ShaderNodeVolumePrincipled")
    volume.name = "fas_volume"
    volume.inputs["Density"].default_value = VOLUME_DENSITY
    volume.inputs["Color"].default_value = (SMOKE_COLOUR, SMOKE_COLOUR, SMOKE_COLOUR, 1.0)
    volume.inputs["Blackbody Intensity"].default_value = BLACKBODY
    output = tree.nodes.new("ShaderNodeOutputMaterial")
    output.location = (300.0, 0.0)
    tree.links.new(volume.outputs["Volume"], output.inputs["Volume"])
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


def create_sim_fire(context, location, name="Simulated Campfire"):
    if not bpy.app.build_options.fluid:
        raise RuntimeError(NO_FLUID)
    scene = context.scene
    kind = C.KIND_SIM_FIRE
    effect_uuid = naming.new_uuid()
    collection = naming.new_effect_collection(scene, kind, effect_uuid, name)

    domain_mesh = naming.tag(_box_mesh(f"{name} Domain", DOMAIN_SIZE, DOMAIN_CENTRE_Z), kind, effect_uuid)
    material = naming.tag(_volume_material(f"FAS_{name}"), kind, effect_uuid)
    domain_mesh.materials.append(material)
    domain = naming.tag(bpy.data.objects.new(name, domain_mesh), kind, effect_uuid)
    domain.location = location
    collection.objects.link(domain)

    emitter_mesh = naming.tag(_disc_mesh(f"{name} Emitter", EMITTER_RADIUS, 0.0), kind, effect_uuid)
    emitter = naming.tag(bpy.data.objects.new(f"{name} Emitter", emitter_mesh), kind, effect_uuid)
    collection.objects.link(emitter)
    emitter.parent = domain
    emitter.location = (0.0, 0.0, EMITTER_Z)
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
    settings.vorticity = VORTICITY
    settings.burning_rate = BURNING_RATE
    settings.use_noise = False
    if bpy.app.build_options.openvdb:
        settings.cache_data_format = "OPENVDB"
    settings.cache_type = "REPLAY"
    settings.resolution_max = RESOLUTION
    settings.fluid_group = collection
    settings.effector_group = collection
    set_range(settings, scene.frame_start, scene.frame_end)
    settings.cache_directory = cache_folder.path_for(effect_uuid)

    light, action = fire_light.build_light(f"{name} Light", **LIGHT)
    for id_block in (light, light.data, action):
        naming.tag(id_block, kind, effect_uuid)
    collection.objects.link(light)
    light.parent = domain
    light.location = (0.0, 0.0, LIGHT_HEIGHT)

    entry = registry.add(scene, kind, effect_uuid, primary=domain, root_collection=collection)
    entry.emitter = emitter
    entry.planes = 0
    entry.light = light
    entry.base_energy = light.data.energy
    light_mode.apply(domain, light, light_mode.REAL)
    entry.light_mode = light_mode.REAL
    entry.base_fuel = emission.fuel_amount
    entry.base_smoke = emission.density
    entry.base_density = VOLUME_DENSITY
    entry.detail = RESOLUTION
    bounces.after_create(scene)
    return effect_uuid
