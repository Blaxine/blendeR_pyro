# SPDX-License-Identifier: GPL-3.0-or-later
"""The 8 presets: each creates and deletes, and what a saved choice means never changes."""

import os
import sys

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fas_testlib as lib  # noqa: E402

import bpy  # noqa: E402
from fire_and_smoke.effects import fire_light, presets  # noqa: E402

# Saved scenes depend on these numbers: new presets go on the end, none ever change.
LOCKED = {"CANDLE": 0, "TORCH": 1, "CAMPFIRE": 2, "BONFIRE": 3, "BURNING_OBJECT": 4,
          "THIN_SMOKE": 5, "BLACK_SMOKE_COLUMN": 6, "EMBERS": 7}


def _tagged():
    groups = ("objects", "meshes", "lights", "materials", "node_groups", "actions", "particles", "collections")
    return [i.name for g in groups for i in getattr(bpy.data, g) if lib.C.OWNER_PROP in i.keys()]


def test_the_catalogue():
    numbers = {p[0]: p[1] for p in presets.PRESETS}
    lib.check("8 presets", len(numbers) == 8)
    for preset_id, number in LOCKED.items():
        lib.check(f"{preset_id} keeps its number", numbers.get(preset_id) == number, str(numbers.get(preset_id)))
    lib.check("numbers are unique", len(set(numbers.values())) == len(numbers))
    shown = [item[4] for item in presets.enum_items()]
    lib.check("the display order uses the same numbers", sorted(shown) == sorted(numbers.values()))
    lib.check("every preset is shown", set(presets.DISPLAY_ORDER) == set(numbers))


def test_preset_choice_doesnt_stick():
    prop = bpy.ops.fas.effect_create.get_rna_type().properties["preset"]
    lib.check("the preset choice uses SKIP_SAVE", prop.is_skip_save)
    prop = bpy.ops.fas.effect_delete.get_rna_type().properties["uuid"]
    lib.check("the delete choice uses SKIP_SAVE", prop.is_skip_save)


def test_every_preset_creates_and_deletes():
    lib.clear_scene()
    lib.add_camera()
    lib.setup_render()
    scene = lib.scene()
    bpy.ops.mesh.primitive_cube_add(size=2.0, location=(0.0, 0.0, 1.0))
    crate = bpy.context.object
    crate.name = "Crate"
    for preset_id in presets.DISPLAY_ORDER:
        bpy.context.view_layer.objects.active = crate
        result = bpy.ops.fas.effect_create(preset=preset_id)
        lib.check(f"{preset_id} creates", result == {"FINISHED"})
        entry = scene.fas_effects[-1]
        lib.check(f"{preset_id} records its preset", entry.preset_id == preset_id)
        bpy.context.view_layer.update()
        if entry.kind != lib.C.KIND_EMBERS:
            modifier = entry.primary.modifiers[0]
            lib.check(f"{preset_id}: no node warnings", not list(modifier.node_warnings),
                      str([w.message for w in modifier.node_warnings]))
            lib.check(f"{preset_id}: covered by the limit",
                      scene.cycles.transparent_max_bounces > lib.instance_count(entry.primary))
        bpy.ops.fas.effect_delete(uuid=entry.uuid)
        lib.check(f"{preset_id} deletes cleanly", not _tagged(), str(_tagged()))
    bpy.data.objects.remove(crate)


def test_sliders_reach_what_they_control():
    bpy.ops.fas.effect_create(preset="CAMPFIRE")
    entry = lib.scene().fas_effects[-1]
    uuid = entry.uuid
    from fire_and_smoke.effects import plane_stack
    modifier = entry.primary.modifiers[0]
    width = plane_stack.get_input(modifier, "Width")
    entry.size = 2.0
    lib.check("Size scales the planes", abs(plane_stack.get_input(modifier, "Width") - width * 2.0) < 1e-4)
    entry.size = 1.0
    tree = modifier.node_group
    material = next(n.inputs["Material"].default_value for n in tree.nodes
                    if n.bl_idname == "GeometryNodeSetMaterial" and "fas_strength" in n.inputs["Material"].default_value.node_tree.nodes)
    value = material.node_tree.nodes["fas_strength"].outputs[0]
    base = value.default_value
    entry.brightness = 0.5
    lib.check("Brightness reaches the material", abs(value.default_value - base * 0.5) < 1e-4)
    entry.brightness = 1.0
    energy = fire_light.get_energy(entry.light.data)
    entry.light_strength = 2.0
    lib.check("Light Strength reaches the flicker", abs(fire_light.get_energy(entry.light.data) - energy * 2.0) < 1e-3)
    lib.scene().frame_set(5)
    entry.light_strength = 1.0
    planes = entry.planes
    limit = lib.scene().cycles.transparent_max_bounces
    entry.layers = 8
    lib.check("Layers updates the plane count", entry.planes > planes, f"{planes} -> {entry.planes}")
    lib.check("and the bounce limit", lib.scene().cycles.transparent_max_bounces > limit)
    entry.preview_facing = "CAMERA"
    lib.check("the preview switch reaches the tree", not plane_stack.get_input(modifier, "Face Viewport"))
    bpy.ops.fas.effect_delete(uuid=uuid)

    bpy.ops.fas.effect_create(preset="THIN_SMOKE")
    entry = lib.scene().fas_effects[-1]
    uuid = entry.uuid
    tree = entry.primary.modifiers[0].node_group
    material = next(n.inputs["Material"].default_value for n in tree.nodes if n.bl_idname == "GeometryNodeSetMaterial")
    value = material.node_tree.nodes["fas_density"].outputs[0]
    base = value.default_value
    entry.density = 2.0
    lib.check("Density reaches the material", abs(value.default_value - base * 2.0) < 1e-4)
    bpy.ops.fas.effect_delete(uuid=uuid)

    bpy.ops.fas.effect_create(preset="EMBERS")
    entry = lib.scene().fas_effects[-1]
    uuid = entry.uuid
    settings = entry.primary.particle_systems[0].settings
    count, size = settings.count, settings.particle_size
    entry.amount = 2.0
    entry.ember_size = 3.0
    lib.check("Amount reaches the particles", settings.count == count * 2, str(settings.count))
    lib.check("Ember Size reaches the particles", abs(settings.particle_size - size * 3.0) < 1e-5)
    bpy.ops.fas.effect_delete(uuid=uuid)


def test_settings_survive_save_and_reload():
    bpy.ops.fas.effect_create(preset="CANDLE")
    entry = lib.scene().fas_effects[-1]
    entry.show_advanced = True
    entry.light_mode = "BOTH"
    entry.preview_facing = "CAMERA"
    uuid = entry.uuid
    path = os.path.join(lib.WORKDIR, "saved.blend")
    bpy.ops.wm.save_as_mainfile(filepath=path)
    bpy.ops.wm.open_mainfile(filepath=path)
    entry = next(e for e in bpy.context.scene.fas_effects if e.uuid == uuid)
    lib.check("settings come back after reload", entry.show_advanced and entry.light_mode == "BOTH"
              and entry.preview_facing == "CAMERA" and entry.preset_id == "CANDLE")
    lib.check("the effect's parts come back", entry.primary is not None and entry.light is not None)
    lib.check("Delete works after reload", bpy.ops.fas.effect_delete(uuid=uuid) == {"FINISHED"})


lib.main(globals())
