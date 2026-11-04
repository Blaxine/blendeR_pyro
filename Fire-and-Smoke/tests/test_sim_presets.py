# SPDX-License-Identifier: GPL-3.0-or-later
"""The Simulated Fire's presets: Normal Fire, Candle Fire and Campfire, chosen at Create
or applied later, marked modified once edited, and never live in a saved scene."""

import json
import os
import sys
import tempfile

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fas_testlib as lib  # noqa: E402

import bpy  # noqa: E402
from fire_and_smoke.effects import fire_light, sim_fire, sim_presets  # noqa: E402

CATALOG = sim_presets.CATALOG


def _entry():
    return lib.scene().fas_effects[-1]


def _create(sim_preset=None):
    if sim_preset is None:
        result = bpy.ops.fas.effect_create(preset="SIMULATED_CAMPFIRE")
    else:
        result = bpy.ops.fas.effect_create(preset="SIMULATED_CAMPFIRE", sim_preset=sim_preset)
    lib.check("Create finishes", result == {"FINISHED"}, str(result))
    return _entry()


def _play(to):
    scene = lib.scene()
    for frame in range(scene.frame_start, to + 1):
        scene.frame_set(frame)


def _flame(entry):
    depsgraph = bpy.context.evaluated_depsgraph_get()
    settings = sim_fire.find_modifier(entry.primary.evaluated_get(depsgraph), "DOMAIN").domain_settings
    flame = list(settings.flame_grid)
    return max(flame) if flame else 0.0


def _grid(entry):
    depsgraph = bpy.context.evaluated_depsgraph_get()
    settings = sim_fire.find_modifier(entry.primary.evaluated_get(depsgraph), "DOMAIN").domain_settings
    return tuple(settings.domain_resolution)


def _emitter_radius(entry):
    return max(v.co.length for v in entry.emitter.data.vertices)


def _matches(entry, preset_id):
    """Everything the package says, read back from the effect."""
    package = CATALOG[preset_id]
    shape, light = package["shape"], package["light"]
    domain, flow = sim_fire.domain_settings(entry), sim_fire.flow_settings(entry)
    node = sim_fire.volume_node(entry)
    problems = []
    size = tuple(entry.primary.dimensions)
    if any(abs(a - b) > 1e-4 for a, b in zip(size, shape["domain_size"])):
        problems.append(f"domain {size}")
    if abs(_emitter_radius(entry) - shape["emitter_radius"]) > 1e-5:
        problems.append(f"emitter radius {_emitter_radius(entry)}")
    if abs(entry.emitter.location.z - shape["emitter_z"]) > 1e-6:
        problems.append("emitter height")
    if abs(entry.light.location.z - shape["light_height"]) > 1e-6:
        problems.append("light height")
    for field, value in package["domain"].items():
        if getattr(domain, field) != value and abs(getattr(domain, field) - value) > 1e-5:
            problems.append(f"domain {field} {getattr(domain, field)}")
    for field, value in package["flow"].items():
        got = getattr(flow, field)
        if got != value and not (isinstance(value, float) and abs(got - value) < 1e-5):
            problems.append(f"flow {field} {got}")
    if domain.resolution_max != package["entry"]["detail"] or entry.detail != package["entry"]["detail"]:
        problems.append(f"detail {entry.detail} {domain.resolution_max}")
    if abs(node.inputs["Density"].default_value - package["material"]["density"]) > 1e-5:
        problems.append("volume density")
    if abs(node.inputs["Color"].default_value[0] - package["material"]["colour"]) > 1e-5:
        problems.append("smoke colour")
    if abs(node.inputs["Blackbody Intensity"].default_value - package["material"]["blackbody"]) > 1e-4:
        problems.append("blackbody")
    if abs(fire_light.get_energy(entry.light.data) - light["energy"]) > 1e-4:
        problems.append(f"light {fire_light.get_energy(entry.light.data)}")
    if abs(entry.light.data.shadow_soft_size - light["radius"]) > 1e-5:
        problems.append("light radius")
    if abs(fire_light.flicker_ratio(entry.light.data) - light["flicker"]) > 1e-5:
        problems.append("flicker")
    if (entry.flame_intensity, entry.smoke_amount, entry.light_strength) != (1.0, 1.0, 1.0):
        problems.append("sliders")
    if entry.sim_preset != preset_id or entry.sim_preset_label != package["label"]:
        problems.append(f"applied {entry.sim_preset} {entry.sim_preset_label}")
    if entry.sim_preset_choice != preset_id or entry.sim_preset_modified or sim_presets.is_modified(entry):
        problems.append("menu or modified")
    return problems


def test_catalogue():
    lib.check("three simulation presets",
              [p["label"] for p in CATALOG.values()] == ["Normal Fire", "Candle Fire", "Campfire"])
    lib.check("each keeps its fixed number", [p["number"] for p in CATALOG.values()] == [1, 2, 3])
    lib.check("the menu starts with Custom, number 0", sim_presets.CHOICES[0][:1] == ("CUSTOM",)
              and sim_presets.CHOICES[0][3] == 0)
    lib.check("Create offers the three, no Custom", [i[0] for i in sim_presets.ITEMS] == list(CATALOG))
    lib.check("Campfire is the default", sim_presets.DEFAULT == sim_presets.CAMPFIRE)
    for preset_id, package in CATALOG.items():
        lib.check(f"{package['label']} sets every snapshotted field",
                  set(package["domain"]) | {"resolution_max"} == set(sim_presets.SNAPSHOT_DOMAIN)
                  and set(package["flow"]) == set(sim_presets.SNAPSHOT_FLOW))
        shape = package["shape"]
        bottom = shape["domain_centre_z"] - shape["domain_size"][2] / 2
        lib.check(f"{package['label']}'s emitter is inside its domain",
                  bottom < shape["emitter_z"] and shape["emitter_radius"] < shape["domain_size"][0] / 2)
        lib.check(f"{package['label']}'s Detail is in the slider's range", 16 <= package["entry"]["detail"] <= 96)


def test_create_each():
    for preset_id, package in CATALOG.items():
        lib.clear_scene()
        lib.add_camera()
        scene = lib.scene()
        scene.frame_start, scene.frame_end = 1, 40
        scene.frame_set(1)
        entry = _create(preset_id)
        problems = _matches(entry, preset_id)
        lib.check(f"{package['label']} is built as its package says", not problems, str(problems))
        lib.check(f"{package['label']} is named for it", entry.primary.name == package["name"], entry.primary.name)
        _play(20)
        flame = _flame(entry)
        lib.check(f"{package['label']} burns", flame > 0.3, f"{flame:.3f}")
        lib.info(f"{package['label']}: flame max {flame:.3f} after 20 frames, "
                 f"grid {_grid(entry)}")
        bpy.ops.fas.effect_delete(uuid=entry.uuid)


def test_default_is_the_campfire():
    lib.clear_scene()
    lib.add_camera()
    entry = _create()
    lib.check("with no choice, Create makes the Campfire", not _matches(entry, sim_presets.CAMPFIRE),
              str(_matches(entry, sim_presets.CAMPFIRE)))
    lib.check("the redo panel offers the simulation preset",
              "sim_preset" in bpy.ops.fas.effect_create.get_rna_type().properties)


def test_apply_another():
    entry = _entry()
    uuid = entry.uuid
    domain, mesh = entry.primary, entry.primary.data
    material = mesh.materials[0]
    emitter = entry.emitter
    tagged = {i.name for g in ("objects", "meshes", "lights", "materials", "actions", "collections")
              for i in getattr(bpy.data, g) if lib.C.OWNER_PROP in i.keys()}
    entry.flame_intensity = 2.0
    entry.light_strength = 0.5
    _play(10)
    before = _flame(entry)
    entry.sim_preset_choice = sim_presets.CANDLE_FIRE
    result = bpy.ops.fas.apply_sim_preset(uuid=uuid)
    entry = _entry()
    lib.check("Apply finishes", result == {"FINISHED"}, str(result))
    problems = _matches(entry, sim_presets.CANDLE_FIRE)
    lib.check("the Campfire becomes a Candle Fire", not problems, str(problems))
    lib.check("on the same objects", entry.primary == domain and entry.primary.data == mesh
              and entry.emitter == emitter and entry.primary.data.materials[0] == material)
    lib.check("which keep their names and ownership",
              tagged == {i.name for g in ("objects", "meshes", "lights", "materials", "actions", "collections")
                         for i in getattr(bpy.data, g) if lib.C.OWNER_PROP in i.keys()})
    lib.check("the domain keeps its material", list(mesh.materials) == [material])
    lib.check("the domain is still where it was", tuple(domain.location) == (0.0, 0.0, 0.0))
    _play(10)
    after = _flame(entry)
    lib.check("the next play from the first frame simulates the candle",
              _grid(entry)[2] == CATALOG[sim_presets.CANDLE_FIRE]["entry"]["detail"] and after > 0.3,
              f"grid {_grid(entry)}, flame before {before:.3f}, after {after:.3f}")
    entry.sim_preset_choice = sim_presets.NORMAL_FIRE
    bpy.ops.fas.apply_sim_preset(uuid=uuid)
    problems = _matches(_entry(), sim_presets.NORMAL_FIRE)
    lib.check("and then a Normal Fire", not problems, str(problems))
    entry = _entry()
    entry.sim_preset_choice = sim_presets.CUSTOM
    try:
        sim_presets.apply(bpy.context, entry, sim_presets.CUSTOM)
        lib.check("applying Custom is refused", False)
    except RuntimeError as exc:
        lib.check("applying Custom is refused plainly", str(exc) == sim_presets.CHOOSE, str(exc))
    lib.check("and changes nothing", entry.sim_preset == sim_presets.NORMAL_FIRE
              and abs(sim_fire.domain_settings(entry).vorticity
                      - CATALOG[sim_presets.NORMAL_FIRE]["domain"]["vorticity"]) < 1e-6)


def test_modified():
    entry = _entry()
    entry.sim_preset_choice = sim_presets.CAMPFIRE
    bpy.ops.fas.apply_sim_preset(uuid=entry.uuid)
    entry = _entry()
    for name, value in (("detail", 48), ("flame_intensity", 1.5), ("smoke_amount", 0.5), ("light_strength", 2.0)):
        bpy.ops.fas.apply_sim_preset(uuid=entry.uuid)
        entry = _entry()
        lib.check(f"Apply clears modified before {name}", not entry.sim_preset_modified
                  and not sim_presets.is_modified(entry))
        setattr(entry, name, value)
        lib.check(f"changing {name} marks it modified", entry.sim_preset_modified)
    bpy.ops.fas.apply_sim_preset(uuid=entry.uuid)
    entry = _entry()
    sim_fire.domain_settings(entry).vorticity = 0.9
    lib.check("an edit in Blender's Physics panel shows as modified", sim_presets.is_modified(entry))
    bpy.context.view_layer.update()
    lib.check("and the depsgraph watch stores it", entry.sim_preset_modified)
    bpy.ops.fas.apply_sim_preset(uuid=entry.uuid)
    entry = _entry()
    sim_fire.flow_settings(entry).fuel_amount = 0.2
    bpy.context.view_layer.update()
    lib.check("an edit to the emitter shows too", entry.sim_preset_modified)
    entry.sim_preset_snapshot = "not json"
    lib.check("a damaged snapshot reads as modified, not as an error", sim_presets.is_modified(entry))
    bpy.ops.fas.apply_sim_preset(uuid=entry.uuid)
    entry = _entry()
    entry.light_mode = "EMISSIVE"
    lib.check("the light mode is the buyer's own choice, not the preset's", not sim_presets.is_modified(entry))
    entry.light_mode = "REAL"


def test_saved_scenes_keep_values():
    entry = _entry()
    bpy.ops.fas.apply_sim_preset(uuid=entry.uuid)
    entry = _entry()
    saved = json.loads(entry.sim_preset_snapshot)
    original = CATALOG[sim_presets.CAMPFIRE]["domain"]["vorticity"]
    CATALOG[sim_presets.CAMPFIRE]["domain"]["vorticity"] = 0.77
    try:
        lib.check("a changed definition doesn't change the fire",
                  abs(sim_fire.domain_settings(entry).vorticity - original) < 1e-6)
        lib.check("or mark it modified", not sim_presets.is_modified(entry))
    finally:
        CATALOG[sim_presets.CAMPFIRE]["domain"]["vorticity"] = original
    path = os.path.join(tempfile.mkdtemp(prefix="fas_presets_"), "presets.blend")
    bpy.ops.wm.save_as_mainfile(filepath=path)
    bpy.ops.wm.open_mainfile(filepath=path)
    entry = _entry()
    lib.check("the applied preset is saved", entry.sim_preset == sim_presets.CAMPFIRE
              and entry.sim_preset_label == "Campfire" and entry.sim_preset_choice == sim_presets.CAMPFIRE)
    lib.check("with its snapshot", json.loads(entry.sim_preset_snapshot) == saved)
    lib.check("and still unmodified after opening", not sim_presets.is_modified(entry))
    bpy.ops.fas.effect_delete(uuid=entry.uuid)


def test_only_simulated_fires():
    lib.clear_scene()
    bpy.ops.fas.effect_create(preset="CAMPFIRE")
    entry = _entry()
    try:
        sim_presets.apply(bpy.context, entry, sim_presets.CAMPFIRE)
        lib.check("a plane fire is refused", False)
    except RuntimeError as exc:
        lib.check("a plane fire is refused plainly", str(exc) == sim_presets.NOT_SIMULATED, str(exc))
    entry.flame_intensity = 2.0
    lib.check("and is never marked modified", not entry.sim_preset_modified)
    bpy.ops.fas.effect_delete(uuid=entry.uuid)


lib.main(globals())
