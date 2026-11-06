# SPDX-License-Identifier: GPL-3.0-or-later
"""Delete touches only what's still the add-on's, and the bounce limit is restored only if ours."""

import os
import sys

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fas_testlib as lib  # noqa: E402

import bpy  # noqa: E402


def _create():
    bpy.ops.fas.campfire_create()
    return lib.scene().fas_effects[-1].uuid


def _entry(uuid):
    return next(e for e in lib.scene().fas_effects if e.uuid == uuid)


def test_renamed_parts_still_go():
    lib.clear_scene()
    uuid = _create()
    entry = _entry(uuid)
    primary, light = entry.primary.name, entry.light.name
    entry.primary.name = "My Bonfire"
    entry.light.name = "My Lamp"
    entry.primary.modifiers[0].name = "Whatever"
    entry.primary.modifiers[0].node_group.name = "My Tree"
    entry.root_collection.name = "My Stuff"
    bpy.ops.fas.effect_delete(uuid=uuid)
    lib.check("renamed objects are gone", "My Bonfire" not in bpy.data.objects and "My Lamp" not in bpy.data.objects
              and primary not in bpy.data.objects and light not in bpy.data.objects)
    lib.check("renamed tree is gone", "My Tree" not in bpy.data.node_groups)
    lib.check("renamed collection is gone", "My Stuff" not in bpy.data.collections)


def test_moving_the_effect_to_my_collection_still_deletes_it():
    uuid = _create()
    primary = _entry(uuid).primary
    mine = bpy.data.collections.new("Mine")
    lib.scene().collection.children.link(mine)
    mine.objects.link(primary)
    _entry(uuid).root_collection.objects.unlink(primary)
    name = primary.name
    bpy.ops.fas.effect_delete(uuid=uuid)
    lib.check("it's gone from my collection", name not in bpy.data.objects)
    lib.check("my collection stays", "Mine" in bpy.data.collections)
    bpy.data.collections.remove(mine)


def test_my_object_in_its_collection_stays():
    uuid = _create()
    bpy.ops.mesh.primitive_cube_add()
    mine = bpy.context.object
    mine.name = "My Log"
    for col in list(mine.users_collection):
        col.objects.unlink(mine)
    _entry(uuid).root_collection.objects.link(mine)
    bpy.ops.fas.effect_delete(uuid=uuid)
    lib.check("my object survives", "My Log" in bpy.data.objects)
    lib.check("and is still in the scene", "My Log" in lib.scene().objects)
    bpy.data.objects.remove(bpy.data.objects["My Log"])


def test_my_child_of_the_fire_keeps_its_place():
    uuid = _create()
    bpy.ops.mesh.primitive_cube_add(location=(3.0, 1.0, 2.0))
    mine = bpy.context.object
    mine.name = "My Child"
    entry = _entry(uuid)
    entry.primary.location = (10.0, 0.0, 0.0)
    bpy.context.view_layer.update()
    world = mine.matrix_world.copy()
    mine.parent = entry.primary
    mine.matrix_parent_inverse = entry.primary.matrix_world.inverted()
    bpy.context.view_layer.update()
    bpy.ops.fas.effect_delete(uuid=uuid)
    bpy.context.view_layer.update()
    lib.check("my child survives", "My Child" in bpy.data.objects and mine.parent is None)
    lib.check("and stays where it was", (mine.matrix_world.translation - world.translation).length < 1e-4,
              str(mine.matrix_world.translation))
    bpy.data.objects.remove(mine)


def test_adopted_light_stays():
    uuid = _create()
    light = _entry(uuid).light
    light.parent = None
    name = light.name
    bpy.ops.fas.effect_delete(uuid=uuid)
    lib.check("a light I unparented stays", name in bpy.data.objects and name in lib.scene().objects)
    lib.check("and is no longer tagged", lib.C.OWNER_PROP not in bpy.data.objects[name].keys())
    lib.check("its data stays too", bpy.data.objects[name].data is not None)
    bpy.data.objects.remove(bpy.data.objects[name])


def test_adopted_material_stays():
    uuid = _create()
    tree = _entry(uuid).primary.modifiers[0].node_group
    material = next(n.inputs["Material"].default_value for n in tree.nodes
                    if n.bl_idname == "GeometryNodeSetMaterial" and "Flame" in n.inputs["Material"].default_value.name)
    bpy.ops.mesh.primitive_cube_add()
    mine = bpy.context.object
    mine.data.materials.append(material)
    name = material.name
    bpy.ops.fas.effect_delete(uuid=uuid)
    lib.check("a material I'm using stays", name in bpy.data.materials)
    lib.check("and is no longer tagged", lib.C.OWNER_PROP not in bpy.data.materials[name].keys())
    bpy.data.objects.remove(mine)
    bpy.data.materials.remove(bpy.data.materials[name])


def test_bounce_limit():
    scene = lib.scene()
    scene.cycles.transparent_max_bounces = 8
    first = _create()
    lib.check("raised above the planes", scene.cycles.transparent_max_bounces == 30,
              str(scene.cycles.transparent_max_bounces))
    second = _create()
    lib.check("two fires lined up are covered", scene.cycles.transparent_max_bounces == 59,
              str(scene.cycles.transparent_max_bounces))
    bpy.ops.fas.effect_delete(uuid=second)
    lib.check("lowered with one left", scene.cycles.transparent_max_bounces == 30,
              str(scene.cycles.transparent_max_bounces))
    bpy.ops.fas.effect_delete(uuid=first)
    lib.check("restored with none left", scene.cycles.transparent_max_bounces == 8,
              str(scene.cycles.transparent_max_bounces))

    uuid = _create()
    scene.cycles.transparent_max_bounces = 77
    bpy.ops.fas.effect_delete(uuid=uuid)
    lib.check("a limit I changed stays", scene.cycles.transparent_max_bounces == 77,
              str(scene.cycles.transparent_max_bounces))

    scene.cycles.transparent_max_bounces = 500
    uuid = _create()
    lib.check("a limit already high enough isn't touched", scene.cycles.transparent_max_bounces == 500)
    bpy.ops.fas.effect_delete(uuid=uuid)
    lib.check("and still isn't", scene.cycles.transparent_max_bounces == 500)
    scene.cycles.transparent_max_bounces = 8


def test_two_fires_in_line_render_without_black():
    lib.clear_scene()
    lib.add_camera()
    lib.setup_render()
    scene = lib.scene()
    scene.cursor.location = (0.0, 0.0, 0.0)
    first = _create()
    scene.cursor.location = (0.0, 2.0, 0.0)
    second = _create()
    scene.cursor.location = (0.0, 0.0, 0.0)
    scene.frame_set(24)
    pixels = lib.render("CYCLES")
    lib.check("no black pixels", lib.darkest(pixels) > 0.05, f"{lib.darkest(pixels):.4f}")
    bpy.ops.fas.effect_delete(uuid=first)
    bpy.ops.fas.effect_delete(uuid=second)


lib.main(globals())
