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
    lib.scene().fas_effects[0].light_mode = mode
    bpy.context.view_layer.update()


def test_setup():
    lib.clear_scene()
    lib.add_camera()
    lib.setup_render(background=(0.02, 0.02, 0.02))
    bpy.ops.mesh.primitive_plane_add(size=40.0)
    bpy.ops.fas.campfire_create()
    entry = lib.scene().fas_effects[0]
    STATE["fire"], STATE["light"] = entry.primary, entry.light
    lib.scene().frame_set(24)


def test_flags():
    fire, light = STATE["fire"], STATE["light"]
    lib.check("Real is the default", light.hide_render is False and not fire.visible_diffuse
              and lib.scene().fas_effects[0].light_mode == "REAL")
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


def _noise(light):
    from fire_and_smoke.effects import fire_light
    fcurve = fire_light._existing_fcurve(light.data)
    return next(m for m in fcurve.modifiers if m.type == "NOISE")


def test_flicker_survives_zero():
    """Every fire kind: Light Strength 0 and back gives the built flicker again."""
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=(4.0, 0.0, 0.5))
    crate = bpy.context.object
    for preset_id in ("CANDLE", "CAMPFIRE", "BONFIRE", "BURNING_OBJECT", "SIMULATED_CAMPFIRE"):
        bpy.context.view_layer.objects.active = crate
        bpy.ops.fas.effect_create(preset=preset_id)
        entry = lib.scene().fas_effects[-1]
        uuid = entry.uuid
        if not lib.check(f"{preset_id} has a fire light", entry.light is not None):
            bpy.ops.fas.effect_delete(uuid=uuid)
            continue
        built = _noise(entry.light).strength
        entry.light_strength = 0.0
        lib.check(f"{preset_id}: no flicker at 0", _noise(entry.light).strength == 0.0)
        entry.light_strength = 1.0
        lib.check(f"{preset_id}: Light Strength 0 and back restores the flicker",
                  abs(_noise(entry.light).strength - built) < 1e-4, f"{_noise(entry.light).strength} against {built}")
        entry.light_strength = 2.0
        lib.check(f"{preset_id}: and it still scales with the strength",
                  abs(_noise(entry.light).strength - built * 2.0) < 1e-4)
        bpy.ops.fas.effect_delete(uuid=uuid)
    bpy.data.objects.remove(crate)


def test_a_flicker_lost_in_an_old_file_comes_back():
    """Lights made before the share was stored: the old code left the noise at 0."""
    from fire_and_smoke.effects import fire_light
    bpy.ops.fas.effect_create(preset="CAMPFIRE")
    entry = lib.scene().fas_effects[-1]
    data = entry.light.data
    del data[fire_light.FLICKER_PROP]
    _noise(entry.light).strength = 0.0
    entry.light_strength = 1.0
    lib.check("an old light gets the default flicker back",
              abs(_noise(entry.light).strength - fire_light.get_energy(data) * fire_light.DEFAULT_FLICKER) < 1e-4,
              str(_noise(entry.light).strength))
    bpy.ops.fas.effect_delete(uuid=entry.uuid)


def test_modes_keep_their_stored_values():
    lib.check("the modes keep their stored values",
              [item[3] for item in light_mode.ITEMS] == [0, 1, 2])


lib.main(globals())
