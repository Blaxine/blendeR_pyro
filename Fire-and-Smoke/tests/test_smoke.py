# SPDX-License-Identifier: GPL-3.0-or-later
"""Smoke on a point and smoke columns: no bake, no black, cleans up, and leaves fire alone."""

import os
import sys

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fas_testlib as lib  # noqa: E402

import bpy  # noqa: E402
from fire_and_smoke.effects import campfire, plane_stack, smoke  # noqa: E402

KINDS = (("smoke_create", lib.C.KIND_SMOKE, smoke.SMOKE), ("column_create", lib.C.KIND_COLUMN, smoke.COLUMN))


def _tagged():
    groups = ("objects", "meshes", "materials", "node_groups", "collections")
    return [i.name for g in groups for i in getattr(bpy.data, g) if lib.C.OWNER_PROP in i.keys()]


def test_setup():
    lib.clear_scene()
    lib.add_camera(location=(0.0, -24.0, 4.0), look_at=(0.0, 0.0, 5.0))
    lib.setup_render(background=(0.5, 0.55, 0.6))


def test_each_kind():
    for operator, kind, stack in KINDS:
        result = getattr(bpy.ops.fas, operator)()
        lib.check(f"{kind} is created", result == {"FINISHED"})
        entry = lib.scene().fas_effects[-1]
        uuid = entry.uuid
        modifier = entry.primary.modifiers[0]
        bpy.context.view_layer.update()
        lib.check(f"{kind}: no node warnings", not list(modifier.node_warnings),
                  str([w.message for w in modifier.node_warnings]))
        planes = stack["Sites"] * stack["Layers"]
        lib.check(f"{kind}: the right planes", lib.instance_count(entry.primary) == planes
                  and entry.planes == planes)
        lib.check(f"{kind}: no fire light", entry.light is None)

        lib.scene().frame_set(10)
        a = lib.render(lib.eevee_id())
        lib.scene().frame_set(40)
        b = lib.render(lib.eevee_id())
        lib.check(f"{kind}: moves with no bake", lib.mean_diff(a, b) > 1e-4, f"{lib.mean_diff(a, b):.5f}")

        cycles = lib.render("CYCLES")
        lib.check(f"{kind}: no black rectangles in Cycles", lib.darkest(cycles) > 0.005 or kind == lib.C.KIND_COLUMN,
                  f"{lib.darkest(cycles):.4f}")
        difference = lib.mean_diff(b, cycles)
        lib.info(f"{kind}: mean pixel difference between engines {difference:.4f}")
        lib.check(f"{kind}: engines match closely", difference < 0.02, f"{difference:.4f}")

        bpy.ops.fas.effect_delete(uuid=uuid)
        lib.check(f"{kind}: Delete cleans up", not _tagged(), str(_tagged()))


def test_column_is_not_black_rectangles():
    bpy.ops.fas.column_create()
    entry = lib.scene().fas_effects[-1]
    uuid = entry.uuid
    lib.scene().frame_set(24)
    limit = lib.scene().cycles.transparent_max_bounces
    lib.check("limit covers the column", limit > entry.planes, str(limit))
    pixels = lib.render("CYCLES")
    width = lib.scene().render.resolution_x
    corner = pixels[4 * (width * 2 + 2):4 * (width * 2 + 2) + 3]
    lib.check("the sky stays visible around it", min(corner) > 0.3, str(corner))
    bpy.ops.fas.effect_delete(uuid=uuid)


def test_campfire_values_unchanged():
    lib.check("the Campfire's stack is unchanged", campfire.CAMPFIRE == {
        "Sites": 7, "Layers": 4, "Spread": 0.42, "Spacing": 0.05, "Width": 1.05, "Height": 1.9, "Seed": 3})
    bpy.ops.fas.campfire_create()
    entry = lib.scene().fas_effects[-1]
    lib.check("and still reaches the modifier",
              plane_stack.get_input(entry.primary.modifiers[0], "Sites") == 7)
    bpy.ops.fas.effect_delete(uuid=entry.uuid)


lib.main(globals())
