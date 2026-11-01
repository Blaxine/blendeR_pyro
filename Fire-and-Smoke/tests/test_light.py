# SPDX-License-Identifier: GPL-3.0-or-later
"""Light modes: what lights the scene, and that Real matches between engines."""

import os
import sys

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fas_testlib as lib  # noqa: E402

import bpy  # noqa: E402
from fire_and_smoke.effects import light_mode  # noqa: E402

STATE = {}


def _mean_red(pixels):
    return sum(pixels[i] for i in range(0, len(pixels), 4)) / (len(pixels) / 4)


def _set(mode):
    bpy.context.view_layer.objects.active = STATE["fire"]
    lib.check(f"{mode} applies", bpy.ops.fas.light_mode(mode=mode) == {"FINISHED"})
    bpy.context.view_layer.update()


def test_setup():
    lib.clear_scene()
    lib.add_camera()
    lib.setup_render(background=(0.02, 0.02, 0.02))
    bpy.ops.mesh.primitive_plane_add(size=40.0)
    before = set(bpy.data.objects)
    bpy.ops.fas.campfire_create()
    new = set(bpy.data.objects) - before
    STATE["fire"] = next(o for o in new if o.type == "MESH")
    STATE["light"] = next(o for o in new if o.type == "LIGHT")
    lib.scene().frame_set(24)


def test_flags():
    fire, light = STATE["fire"], STATE["light"]
    lib.check("Real is the default", light.hide_render is False and not fire.visible_diffuse)
    _set("EMISSIVE")
    lib.check("Emissive: light off, planes light the scene",
              light.hide_render and fire.visible_diffuse and fire.visible_glossy)
    _set("BOTH")
    lib.check("Both: light on, planes light the scene",
              not light.hide_render and fire.visible_diffuse and fire.visible_glossy)
    _set("REAL")
    lib.check("Real: light on, planes hidden from the scene's rays",
              not light.hide_render and not fire.visible_diffuse and not fire.visible_glossy)
    lib.check("planes never cast shadows", not fire.visible_shadow)


def test_real_matches_between_engines():
    _set("REAL")
    cycles, eevee = _mean_red(lib.render("CYCLES")), _mean_red(lib.render(lib.eevee_id()))
    difference = abs(cycles - eevee) / max(cycles, eevee)
    lib.info(f"Real mean red: Cycles {cycles:.4f}, EEVEE {eevee:.4f}, {difference:.1%} apart")
    lib.check("Real's brightness is close across engines", difference < 0.1, f"{difference:.1%}")


def test_emissive_lights_the_ground_in_cycles():
    _set("REAL")
    real = lib.render("CYCLES")
    STATE["light"].hide_render = True
    dark = lib.render("CYCLES")
    STATE["light"].hide_render = False
    _set("EMISSIVE")
    emissive = lib.render("CYCLES")
    lib.info(f"Mean red in Cycles: no light {_mean_red(dark):.4f}, emissive {_mean_red(emissive):.4f}, "
             f"real {_mean_red(real):.4f}")
    lib.check("the flames light the scene", _mean_red(emissive) > _mean_red(dark) * 1.1)
    _set("REAL")


def test_needs_a_fire():
    bpy.context.view_layer.objects.active = None
    try:
        bpy.ops.fas.light_mode(mode="BOTH")
        lib.check("refuses with nothing selected", False)
    except RuntimeError as exc:
        lib.check("refuses with nothing selected", "Select a fire" in str(exc), str(exc))
    lib.check("the modes keep their stored values",
              [item[3] for item in light_mode.ITEMS] == [0, 1, 2])


lib.main(globals())
