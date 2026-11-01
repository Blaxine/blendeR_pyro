# SPDX-License-Identifier: GPL-3.0-or-later
"""Copied scenes: effects get their own identity, and deleting in one leaves the other working."""

import os
import sys

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fas_testlib as lib  # noqa: E402

import bpy  # noqa: E402
from fire_and_smoke.core import copies, delete, naming  # noqa: E402

OWNER = lib.C.OWNER_PROP


def _copy(kind):
    before = set(bpy.data.scenes)
    source = bpy.context.window.scene
    bpy.ops.scene.new(type=kind)
    new = next(iter(set(bpy.data.scenes) - before))
    bpy.context.window.scene = source
    return new


def _fresh_scene():
    scene = bpy.data.scenes.new("Fresh")
    bpy.context.window.scene = scene
    return scene


def _works(entry):
    """The effect's own parts are all present and it evaluates."""
    if entry.primary is None or entry.light is None or entry.root_collection is None:
        return False
    return entry.primary.modifiers[0].node_group is not None


def _flickers(entry):
    action = entry.light.data.animation_data.action
    return action is not None and naming.owned_by(action, entry.uuid)


def test_full_copy_gets_its_own_identity():
    scene = _fresh_scene()
    bpy.ops.fas.campfire_create()
    original = scene.fas_effects[0]
    copy_scene = _copy("FULL_COPY")
    copies.reidentify()
    copied = copy_scene.fas_effects[0]
    lib.check("the copy has a new ID", copied.uuid != original.uuid)
    lib.check("the copy's objects carry the new ID", naming.owned_by(copied.primary, copied.uuid)
              and naming.owned_by(copied.light, copied.uuid))
    lib.check("and the original keeps its own", naming.owned_by(original.primary, original.uuid))
    tree_a = original.primary.modifiers[0].node_group
    tree_b = copied.primary.modifiers[0].node_group
    lib.check("the copy has its own node tree", tree_a != tree_b and naming.owned_by(tree_b, copied.uuid))
    materials = [n.inputs["Material"].default_value for n in tree_b.nodes if n.bl_idname == "GeometryNodeSetMaterial"]
    lib.check("and its own materials", all(naming.owned_by(m, copied.uuid) for m in materials), str(materials))
    lib.check("the light flicker carried over", _flickers(copied))
    lib.check("the copy has its own view target", copy_scene.fas_view_target != scene.fas_view_target
              and copy_scene.fas_view_target.name in copy_scene.objects)


def test_delete_in_the_copy_leaves_the_original():
    scene = next(s for s in bpy.data.scenes if s.name == "Fresh")
    copy_scene = next(s for s in bpy.data.scenes if s.name.startswith("Fresh."))
    uuid = copy_scene.fas_effects[0].uuid
    delete.delete_effect(copy_scene, uuid)
    original = scene.fas_effects[0]
    lib.check("the original still works", _works(original) and _flickers(original))
    bpy.context.window.scene = scene
    bpy.context.view_layer.update()
    lib.check("and still evaluates", lib.instance_count(original.primary) == 29)
    lib.check("nothing of the copy's is left", not [
        o.name for o in bpy.data.objects if naming.owned_by(o, uuid)])
    delete.delete_effect(scene, original.uuid)
    bpy.data.scenes.remove(copy_scene)


def test_delete_in_the_original_leaves_the_copy():
    scene = next(s for s in bpy.data.scenes if s.name == "Fresh")
    bpy.ops.fas.campfire_create()
    copy_scene = _copy("FULL_COPY")
    copies.reidentify()
    delete.delete_effect(scene, scene.fas_effects[0].uuid)
    copied = copy_scene.fas_effects[0]
    lib.check("the copy still works", _works(copied) and _flickers(copied))
    lib.check("its tree still has its material", all(
        n.inputs["Material"].default_value is not None
        for n in copied.primary.modifiers[0].node_group.nodes if n.bl_idname == "GeometryNodeSetMaterial"))
    bpy.context.window.scene = copy_scene
    bpy.context.view_layer.update()
    lib.check("and still evaluates", lib.instance_count(copied.primary) == 29)
    delete.delete_effect(copy_scene, copied.uuid)
    lib.check("then it can be deleted too", not [
        i.name for g in ("objects", "meshes", "lights", "materials", "node_groups", "actions", "collections")
        for i in getattr(bpy.data, g) if OWNER in i.keys()])
    bpy.context.window.scene = scene
    bpy.data.scenes.remove(copy_scene)


def test_linked_copy_shares_and_detaches():
    scene = next(s for s in bpy.data.scenes if s.name == "Fresh")
    bpy.ops.fas.campfire_create()
    bpy.ops.fas.campfire_create()
    linked = _copy("LINK_COPY")
    lib.check("a linked copy keeps the same effects", linked.fas_effects[0].uuid == scene.fas_effects[0].uuid
              and linked.fas_effects[0].primary == scene.fas_effects[0].primary)
    first, second = scene.fas_effects[0].uuid, scene.fas_effects[1].uuid
    primary = linked.fas_effects[0].primary
    delete.delete_effect(linked, first)
    lib.check("Delete in the linked copy keeps the objects", primary.name in bpy.data.objects)
    lib.check("the original still has it", primary.name in scene.objects and len(scene.fas_effects) == 2)
    lib.check("the linked copy no longer shows it", primary.name not in linked.objects)
    other = linked.fas_effects[0].primary
    lib.check("the linked copy keeps its other effect", other.name in linked.objects, other.name)
    delete.delete_effect(linked, second)
    lib.check("the original keeps both", len(scene.fas_effects) == 2
              and all(e.primary is not None for e in scene.fas_effects))
    bpy.context.window.scene = scene
    bpy.data.scenes.remove(linked)
    delete.delete_effect(scene, first)
    delete.delete_effect(scene, second)


def test_copies_are_noticed_without_being_asked():
    scene = next(s for s in bpy.data.scenes if s.name == "Fresh")
    bpy.ops.fas.campfire_create()
    copy_scene = _copy("FULL_COPY")
    scene.fas_effects[0].primary.location.x += 1.0  # anything that makes a depsgraph update
    bpy.context.view_layer.update()
    lib.check("the handler gave the copy its own ID",
              copy_scene.fas_effects[0].uuid != scene.fas_effects[0].uuid)
    copies.reidentify()
    delete.delete_effect(copy_scene, copy_scene.fas_effects[0].uuid)
    delete.delete_effect(scene, scene.fas_effects[0].uuid)


lib.main(globals())
