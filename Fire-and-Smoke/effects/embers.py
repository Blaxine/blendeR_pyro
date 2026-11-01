# SPDX-License-Identifier: GPL-3.0-or-later
"""Embers: a legacy particle system on an owned emitter.

Particles have a cache, so unlike flames and smoke they replay from the start when
scrubbed.  The store page has to say so.
"""

import bpy

from .. import constants as C
from ..core import bounces, delete, naming, registry


def _ember_material(name, strength):
    material = bpy.data.materials.new(name)
    material.use_nodes = True
    tree = material.node_tree
    tree.nodes.clear()
    # Object Info's random value is per instance in both engines; Particle Info isn't.
    info = tree.nodes.new("ShaderNodeObjectInfo")
    ramp = tree.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].color = (1.0, 0.09, 0.005, 1.0)
    ramp.color_ramp.elements[1].color = (1.0, 0.42, 0.06, 1.0)
    tree.links.new(info.outputs["Random"], ramp.inputs["Fac"])
    emission = tree.nodes.new("ShaderNodeEmission")
    emission.inputs["Strength"].default_value = strength
    tree.links.new(ramp.outputs["Color"], emission.inputs["Color"])
    output = tree.nodes.new("ShaderNodeOutputMaterial")
    tree.links.new(emission.outputs[0], output.inputs["Surface"])
    return material


def _spark_mesh(name):
    """A small faceted shape: at this size nothing more is visible."""
    mesh = bpy.data.meshes.new(name)
    r = 1.0
    mesh.from_pydata([(r, 0, 0), (-r, 0, 0), (0, r, 0), (0, -r, 0), (0, 0, r), (0, 0, -r)], [],
                     [(0, 2, 4), (2, 1, 4), (1, 3, 4), (3, 0, 4), (2, 0, 5), (1, 2, 5), (3, 1, 5), (0, 3, 5)])
    mesh.update()
    return mesh


def _emitter_mesh(name, radius):
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata([(-radius, -radius, 0), (radius, -radius, 0), (radius, radius, 0), (-radius, radius, 0)],
                     [], [(0, 1, 2, 3)])
    mesh.update()
    return mesh


def create_embers(context, location, count=220, radius=0.45, lifetime=70, speed=1.5, size=0.012,
                  strength=18.0, name="Embers"):
    scene = context.scene
    kind = C.KIND_EMBERS
    effect_uuid = naming.new_uuid()
    collection = naming.new_effect_collection(scene, kind, effect_uuid)

    emitter_mesh = naming.tag(_emitter_mesh(name, radius), kind, effect_uuid)
    emitter = naming.tag(bpy.data.objects.new(name, emitter_mesh), kind, effect_uuid)
    emitter.location = location
    emitter.show_instancer_for_render = False
    emitter.show_instancer_for_viewport = False
    collection.objects.link(emitter)

    material = naming.tag(_ember_material(f"FAS_{name}", strength), kind, effect_uuid)
    spark_mesh = naming.tag(_spark_mesh(f"{name} Spark"), kind, effect_uuid)
    spark_mesh.materials.append(material)
    spark = naming.tag(bpy.data.objects.new(f"{name} Spark", spark_mesh), kind, effect_uuid)
    spark.parent = emitter
    collection.objects.link(spark)
    # Only its instances show; the original stays out of the way.
    spark.hide_render = True
    spark.hide_viewport = True
    spark.hide_select = True

    modifier = emitter.modifiers.new(name, "PARTICLE_SYSTEM")
    settings = modifier.particle_system.settings
    naming.tag(settings, kind, effect_uuid)
    settings.name = f"FAS_{name}"
    settings.count = count
    settings.frame_start = scene.frame_start
    settings.frame_end = scene.frame_end
    settings.lifetime = lifetime
    settings.lifetime_random = 0.6
    settings.emit_from = "FACE"
    settings.normal_factor = speed
    settings.factor_random = speed * 0.45
    settings.brownian_factor = 0.6
    settings.drag_factor = 0.15
    settings.effector_weights.gravity = -0.05
    settings.render_type = "OBJECT"
    settings.instance_object = spark
    settings.particle_size = size
    settings.size_random = 0.7
    settings.use_rotations = True
    settings.rotation_mode = "NOR"
    settings.angular_velocity_mode = "RAND"
    settings.angular_velocity_factor = 4.0
    settings.display_method = "RENDER"
    settings.use_dead = False
    settings.show_unborn = False

    entry = registry.add(scene, kind, effect_uuid, primary=emitter, root_collection=collection)
    entry.instance = spark
    bounces.after_create(scene)
    return effect_uuid


class FAS_OT_embers_create(bpy.types.Operator):
    bl_idname = "fas.embers_create"
    bl_label = "Add Embers"
    bl_description = "Add rising embers at the 3D cursor. They replay from the start when you scrub"
    bl_options = {"REGISTER", "UNDO"}

    @delete.guarded_create
    def execute(self, context):
        create_embers(context, context.scene.cursor.location)
        return {"FINISHED"}


CLASSES = (FAS_OT_embers_create,)
