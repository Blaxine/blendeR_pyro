# SPDX-License-Identifier: GPL-3.0-or-later
"""The Simulated Fire's look: Flame Colour, Emission Strength, Temperature, Density and
Smoke Colour.  They're the volume material's, so they show straight away, with no new
simulation, and Apply puts the preset's look back."""

import os
import sys

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fas_testlib as lib  # noqa: E402

import bpy  # noqa: E402
from fire_and_smoke.effects import fire_light, sim_fire, sim_presets  # noqa: E402
from fire_and_smoke.ui import control_spec  # noqa: E402
from mathutils import Vector  # noqa: E402

CATALOG = sim_presets.CATALOG
LOOK = ("flame_tint", "emission_strength", "fire_temperature", "volume_density", "smoke_colour")
STATE = {}


def _entry():
    return [e for e in lib.scene().fas_effects if e.kind == lib.C.KIND_SIM_FIRE][-1]


def _close(a, b, tolerance=1e-4):
    a = tuple(a) if hasattr(a, "__len__") else (a,)
    b = tuple(b) if hasattr(b, "__len__") else (b,)
    return len(a) == len(b) and all(abs(x - y) < tolerance for x, y in zip(a, b))


class _Clears:
    def __enter__(self):
        self.cleared = []
        self.original = sim_fire.clear_cache
        sim_fire.clear_cache = lambda entry: (self.cleared.append(entry.uuid), self.original(entry))
        return self

    def __exit__(self, *_args):
        sim_fire.clear_cache = self.original


def _render(name):
    """A small Cycles render of the frame on screen: its linear (red, green, blue) on
    average, unclipped, so a bright flame still shows a change."""
    scene = lib.scene()
    scene.render.image_settings.file_format = "OPEN_EXR"
    scene.render.filepath = os.path.join(STATE["folder"], f"{name}.exr")
    bpy.ops.render.render(write_still=True)
    image = bpy.data.images.load(scene.render.filepath)
    pixels = list(image.pixels)
    bpy.data.images.remove(image)
    count = len(pixels) // 4
    return tuple(sum(pixels[i::4]) / count for i in range(3))


def test_controls():
    lib.clear_scene()
    scene = lib.scene()
    scene.cursor.location = (0.0, 0.0, 0.0)
    scene.frame_start, scene.frame_end = 1, 40
    scene.frame_set(1)
    bpy.ops.fas.effect_create(preset="SIMULATED_CAMPFIRE")
    entry = _entry()
    STATE["uuid"] = entry.uuid
    spec = control_spec.controls(entry.kind, False)
    lib.check("the box shows the look controls", all(f"entry:{name}" in spec for name in LOOK), str(spec))
    lib.check("after the simulation's own", spec.index("entry:flame_tint") > spec.index("entry:smoke_amount"))
    node = sim_fire.volume_node(entry)
    material = CATALOG[sim_presets.CAMPFIRE]["material"]
    lib.check("Flame Colour starts white, keeping the preset's colours",
              _close(entry.flame_tint, (1.0, 1.0, 1.0)) and _close(node.inputs["Blackbody Tint"].default_value[:3],
                                                                    (1.0, 1.0, 1.0)))
    lib.check("Smoke Colour starts as the preset's", _close(entry.smoke_colour, (material["colour"],) * 3)
              and _close(node.inputs["Color"].default_value[:3], (material["colour"],) * 3))
    lib.check("Temperature starts at Blender's own", _close(node.inputs["Temperature"].default_value,
                                                            sim_fire.TEMPERATURE))


def test_each_slider_sets_the_material():
    entry = _entry()
    node = sim_fire.volume_node(entry)
    ramp, strength, tint, heat = sim_fire.flame_nodes(entry)
    material = CATALOG[sim_presets.CAMPFIRE]["material"]
    with _Clears() as clears:
        entry.emission_strength = 2.0
        entry.fire_temperature = 1.5
        entry.flame_tint = (1.0, 0.5, 0.25)
        entry.volume_density = 2.0
        entry.smoke_colour = (0.2, 0.1, 0.05)
    lib.check("none of them simulates again", not clears.cleared, str(clears.cleared))
    lib.check("a vivid Flame Colour colours the ramp, keeping its brightness",
              _close(tint.inputs["Factor"].default_value, 0.75)
              and _close(sim_fire._socket(tint.inputs, "B_Color").default_value[:3], (1.0, 0.5, 0.25)))
    lib.check("Emission Strength and Temperature brighten the flame ramp",
              _close(strength.inputs[1].default_value, material["flame_colour"] * 2.0 * 1.5),
              f"{strength.inputs[1].default_value}")
    lib.check("and blackbody", _close(node.inputs["Blackbody Intensity"].default_value, material["blackbody"] * 2.0))
    lib.check("Temperature heats the volume", _close(node.inputs["Temperature"].default_value,
                                                     sim_fire.TEMPERATURE * 1.5))
    lib.check("and reads further up the ramp", _close(heat.inputs[1].default_value, 1.5))
    entry.flame_tint = (0.5, 0.25, 0.125)
    lib.check("a darker one glows less", _close(strength.inputs[1].default_value,
                                                material["flame_colour"] * 2.0 * 1.5 * 0.5))
    entry.flame_tint = (1.0, 0.5, 0.25)
    lib.check("and the fire light takes its hue", _close(entry.light.data.color, sim_fire.light_colour((1.0, 0.5, 0.25))))
    entry.flame_tint = (0.2, 0.5, 1.0)
    red, _green, blue = entry.light.data.color
    lib.check("so a blue fire lights the scene blue", blue > red, str(tuple(entry.light.data.color)))
    entry.flame_tint = (1.0, 0.5, 0.25)
    lib.check("Flame Colour tints blackbody", _close(node.inputs["Blackbody Tint"].default_value[:3], (1.0, 0.5, 0.25)))
    lib.check("Density thickens the volume", _close(node.inputs["Density"].default_value, material["density"] * 2.0))
    entry.smoke_amount = 0.5
    lib.check("with Smoke as well", _close(node.inputs["Density"].default_value, material["density"] * 2.0 * 0.5))
    entry.smoke_amount = 1.0
    lib.check("Smoke Colour colours the smoke", _close(node.inputs["Color"].default_value[:3], (0.2, 0.1, 0.05)))
    lib.check("an edit marks the preset modified", sim_presets.is_modified(entry))


def test_apply_puts_the_look_back():
    entry = _entry()
    bpy.ops.fas.apply_sim_preset(uuid=entry.uuid)
    entry = _entry()
    node = sim_fire.volume_node(entry)
    _ramp, strength, tint, heat = sim_fire.flame_nodes(entry)
    material = CATALOG[sim_presets.CAMPFIRE]["material"]
    lib.check("the sliders go back", (entry.emission_strength, entry.fire_temperature, entry.volume_density)
              == (1.0, 1.0, 1.0) and _close(entry.flame_tint, (1.0, 1.0, 1.0)))
    lib.check("and the material", _close(strength.inputs[1].default_value, material["flame_colour"])
              and _close(node.inputs["Density"].default_value, material["density"])
              and _close(heat.inputs[1].default_value, 1.0) and _close(tint.inputs["Factor"].default_value, 0.0)
              and _close(node.inputs["Color"].default_value[:3], (material["colour"],) * 3))
    lib.check("the light is the fire's own orange again", _close(entry.light.data.color, fire_light.COLOUR))
    lib.check("not modified", not sim_presets.is_modified(entry))


def test_blackbody_presets():
    """Normal Fire glows from blackbody, not the ramp: the sliders still work on it."""
    entry = _entry()
    entry.sim_preset_choice = sim_presets.NORMAL_FIRE
    bpy.ops.fas.apply_sim_preset(uuid=entry.uuid)
    entry = _entry()
    node = sim_fire.volume_node(entry)
    material = CATALOG[sim_presets.NORMAL_FIRE]["material"]
    entry.emission_strength = 0.5
    lib.check("Emission Strength scales its blackbody",
              _close(node.inputs["Blackbody Intensity"].default_value, material["blackbody"] * 0.5))
    lib.check("and leaves the ramp dark", _close(sim_fire.flame_colour(entry)[1].inputs[1].default_value, 0.0))
    entry.sim_preset_choice = sim_presets.CAMPFIRE
    bpy.ops.fas.apply_sim_preset(uuid=entry.uuid)


def test_an_older_fire_keeps_its_look():
    entry = _entry()
    node = sim_fire.volume_node(entry)
    tree = node.id_data
    for name in (sim_fire.TINT_NODE, sim_fire.HEAT_NODE):
        tree.nodes.remove(tree.nodes[name])
    for key in ("base_blackbody", "base_emission", "smoke_colour"):
        del entry[key]
    node.inputs["Color"].default_value = (0.3, 0.3, 0.3, 1.0)
    strength_before = sim_fire.flame_colour(entry)[1].inputs[1].default_value
    entry.emission_strength = 2.0
    _ramp, strength, tint, heat = sim_fire.flame_nodes(entry)
    lib.check("its missing nodes are added", tint is not None and heat is not None)
    lib.check("its glow is what the slider scales", _close(strength.inputs[1].default_value, strength_before * 2.0),
              f"{strength_before} -> {strength.inputs[1].default_value}")
    lib.check("and its smoke keeps its colour", _close(node.inputs["Color"].default_value[:3], (0.3,) * 3)
              and _close(entry.smoke_colour, (0.3,) * 3))
    bpy.ops.fas.apply_sim_preset(uuid=entry.uuid)


def test_a_render_shows_it():
    import tempfile
    STATE["folder"] = tempfile.mkdtemp(prefix="fas_look_")
    scene = lib.scene()
    scene.render.engine = "CYCLES"
    scene.cycles.samples = 8
    scene.cycles.use_denoising = False
    scene.render.resolution_x, scene.render.resolution_y = 48, 72
    scene.render.resolution_percentage = 100
    # A black sky, so only the fire counts.
    world = scene.world or bpy.data.worlds.new("Sky")
    scene.world = world
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.0
    camera = bpy.data.objects.new("Camera", bpy.data.cameras.new("Camera"))
    scene.collection.objects.link(camera)
    scene.camera = camera
    camera.location = (0.0, -5.0, 1.0)
    camera.rotation_euler = (Vector((0.0, 0.0, 0.9)) - camera.location).to_track_quat("-Z", "Y").to_euler()
    entry = _entry()
    entry.light_strength = 0.0
    for frame in range(1, 31):
        scene.frame_set(frame)
    base = _render("base")
    lib.info(f"default rgb {tuple(round(c, 4) for c in base)}")
    lib.check("the fire renders", sum(base) > 0.01, str(base))
    entry.flame_tint = (0.3, 0.5, 1.0)
    blue = _render("blue")
    lib.check("a blue Flame Colour renders bluer, with no new simulation",
              blue[2] / max(blue[0], 1e-6) > 2.0 * base[2] / max(base[0], 1e-6), f"{base} -> {blue}")
    entry.flame_tint = (1.0, 1.0, 1.0)
    entry.emission_strength = 2.0
    bright = _render("bright")
    lib.check("Emission Strength brightens it", sum(bright) > 1.5 * sum(base), f"{sum(base):.4f} -> {sum(bright):.4f}")
    entry.emission_strength = 1.0
    entry.fire_temperature = 0.6
    cool = _render("cool")
    lib.check("a cooler fire is dimmer and redder", sum(cool) < sum(base)
              and cool[1] / max(cool[0], 1e-6) < base[1] / max(base[0], 1e-6), f"{base} -> {cool}")
    entry.fire_temperature = 1.0
    entry.light_strength = 1.0
    scene.frame_set(1)


lib.main(globals())
