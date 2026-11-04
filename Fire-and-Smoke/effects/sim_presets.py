# SPDX-License-Identifier: GPL-3.0-or-later
"""The Simulated Fire's presets: Normal Fire, Candle Fire and Campfire.

They work the way AquaSuite's liquid presets do.  Each is plain data, an editable
starting point applied once: at Create, or later with the effect's Preset menu and
Apply.  Applying one writes its values onto the effect and stores a snapshot of what it
wrote, so the panel can say "(modified)" once anything changes, in this panel or in
Blender's Physics panel.  Saved scenes keep the values, never a live reference to these
definitions: changing a package here never changes a fire someone already made.

Saved scenes store the menu's number, so each number is fixed for good: a new preset
gets the next number.
"""

import contextlib
import json
import math
from functools import lru_cache

import bpy

from .. import constants as C

CUSTOM = "CUSTOM"
NORMAL_FIRE = "NORMAL_FIRE"
CANDLE_FIRE = "CANDLE_FIRE"
CAMPFIRE = "CAMPFIRE"
DEFAULT = CAMPFIRE

NOT_SIMULATED = "Only a Simulated Fire takes a simulation preset"
CHOOSE = "Choose a preset to apply"
NO_DOMAIN = "This fire's simulation is gone. Delete it to clean up the rest"

_applying = set()


def _package(number, label, name, description, *, domain_size, domain_centre_z, emitter_radius=None,
             resolution, vorticity, burning_rate, volume_density, smoke_colour, light_energy,
             light_radius, light_height, emitter_z=0.05, emitter_patches=None, flame_smoke=1.0,
             heat_buoyancy=1.0, flame_max_temp=3.0, flame_vorticity=0.5, flow_type="BOTH", fuel=1.0,
             smoke=1.0, temperature=1.0, blackbody=1.0, flame_colour=0.0, flicker=0.3, flicker_speed=3.0):
    # The defaults are Blender's own, so a preset only names what it changes.
    if emitter_patches:
        emitter_radius = max(math.hypot(x, y) + r for x, y, _z, r in emitter_patches)
    return {
        "number": number, "label": label, "name": name, "description": description,
        # Sizes in metres, from the domain's origin at the 3D cursor.
        # emitter_patches, when given, are (x, y, z, radius) discs from the emitter's origin,
        # and emitter_radius is how far they reach.
        "shape": {"emitter_radius": emitter_radius, "emitter_z": emitter_z, "domain_size": domain_size,
                  "domain_centre_z": domain_centre_z, "light_height": light_height,
                  "emitter_patches": tuple(emitter_patches or ())},
        "entry": {"detail": resolution},
        "domain": {"vorticity": vorticity, "burning_rate": burning_rate, "flame_smoke": flame_smoke,
                   "beta": heat_buoyancy, "flame_max_temp": flame_max_temp, "flame_vorticity": flame_vorticity},
        "flow": {"flow_type": flow_type, "fuel_amount": fuel, "density": smoke, "temperature": temperature},
        "material": {"density": volume_density, "colour": smoke_colour, "blackbody": blackbody,
                     "flame_colour": flame_colour},
        "light": {"energy": light_energy, "radius": light_radius, "flicker": flicker, "speed": flicker_speed},
    }


# (x, y, z, radius) in metres, from the emitter's origin.
CAMPFIRE_LOGS = ((0.0, 0.0, 0.1, 0.11), (0.24, 0.06, 0.04, 0.09), (-0.22, 0.13, 0.05, 0.1),
                 (0.07, -0.25, 0.03, 0.09), (-0.15, -0.2, 0.06, 0.08), (0.16, 0.26, 0.02, 0.07),
                 (-0.3, -0.03, 0.03, 0.07), (0.3, -0.15, 0.02, 0.06))

# Tuned by render in Cycles on 5.2.2 (docs/LOOK_TEST.md), pending the owner's verdict.
CATALOG = {
    # Half the heat buoyancy and a faster burn keep the flame low, with grey smoke above.
    NORMAL_FIRE: _package(
        1, "Normal Fire", "Simulated Fire", "A knee-high fire with grey smoke rising from it",
        emitter_radius=0.2, emitter_z=0.03, domain_size=(0.9, 0.9, 1.8), domain_centre_z=0.85,
        resolution=64, vorticity=0.3, burning_rate=1.3, heat_buoyancy=0.6, flame_max_temp=3.5,
        volume_density=2.0, smoke_colour=0.15, blackbody=1.5,
        light_energy=20.0, light_radius=0.2, light_height=0.3, flicker=0.25),
    # At full heat buoyancy a 1 cm flame burns the whole domain's height: a tenth of it
    # and a fast burn give a flame about 4 cm tall.  The domain is so small that 96
    # divisions cost less than the Campfire's 64.  A thin flame needs a strong, hot
    # blackbody to read as white-hot at the base.
    CANDLE_FIRE: _package(
        2, "Candle Fire", "Simulated Candle", "A small steady flame with no smoke, for a candle or lamp",
        emitter_radius=0.005, emitter_z=0.005, domain_size=(0.06, 0.06, 0.16), domain_centre_z=0.075,
        resolution=96, vorticity=0.0, burning_rate=4.0, heat_buoyancy=0.1, flame_max_temp=6.0,
        flame_smoke=0.0, flow_type="FIRE", smoke=0.0, volume_density=1.0, smoke_colour=0.05,
        blackbody=25.0, light_energy=0.5, light_radius=0.02, light_height=0.03, flicker=0.12,
        flicker_speed=5.0),
    # A real campfire burns from several logs, not one disc: eight patches at different
    # heights, about 0.6 m across, each give their own tongue of flame.  Strong flame
    # vorticity breaks the tongues up so they change shape from frame to frame, and the
    # flame colour shades from a pale core to deep red tips instead of a blackbody glow.
    CAMPFIRE: _package(
        3, "Campfire", "Simulated Campfire", "A waist-high fire with dark, thin smoke above it",
        emitter_patches=CAMPFIRE_LOGS, domain_size=(1.4, 1.4, 2.6),
        domain_centre_z=1.25, resolution=64, vorticity=0.5, flame_vorticity=1.5, burning_rate=0.9,
        volume_density=3.0, smoke_colour=0.05, blackbody=0.0, flame_colour=7.0,
        light_energy=45.0, light_radius=0.3, light_height=0.5),
}

# Kept alive at module level for Blender's enum API.
ITEMS = [(key, p["label"], p["description"], p["number"]) for key, p in CATALOG.items()]
CHOICES = [(CUSTOM, "Custom", "No preset selected", 0)] + ITEMS


def label(preset_id):
    package = CATALOG.get(preset_id)
    return package["label"] if package else ""


def name(preset_id):
    return CATALOG.get(preset_id, CATALOG[DEFAULT])["name"]


@contextlib.contextmanager
def applying(entry):
    """Changes made while applying a preset don't count as the buyer's edits."""
    nested = entry.uuid in _applying
    _applying.add(entry.uuid)
    try:
        yield
    finally:
        if not nested:
            _applying.discard(entry.uuid)


def busy(entry):
    return entry.uuid in _applying


# --- What a preset wrote, and whether it's still there ----------------------------

SNAPSHOT_ENTRY = ("detail", "flame_intensity", "smoke_amount", "light_strength")
SNAPSHOT_DOMAIN = ("resolution_max",) + tuple(CATALOG[DEFAULT]["domain"])
SNAPSHOT_FLOW = tuple(CATALOG[DEFAULT]["flow"])


def _value(value):
    if isinstance(value, float):
        return round(value, 5)
    if isinstance(value, (str, bool, int)):
        return value
    return [_value(v) for v in value]


def _sources(entry):
    from . import sim_fire
    return {"entry": entry, "domain": sim_fire.domain_settings(entry), "flow": sim_fire.flow_settings(entry)}


def snapshot(entry, fields=None):
    fields = fields or {"entry": SNAPSHOT_ENTRY, "domain": SNAPSHOT_DOMAIN, "flow": SNAPSHOT_FLOW}
    sources = _sources(entry)
    return {group: {field: _value(getattr(sources[group], field)) for field in names
                    if sources[group] is not None and hasattr(sources[group], field)}
            for group, names in fields.items()}


@lru_cache(maxsize=256)
def _decoded(encoded):
    return json.loads(encoded)


def is_modified(entry):
    if entry.sim_preset_modified:
        return True
    if not entry.sim_preset or not entry.sim_preset_snapshot:
        return False
    try:
        saved = _decoded(entry.sim_preset_snapshot)
        return snapshot(entry, saved) != saved
    except (ValueError, TypeError):
        return True


def note_edit(entry):
    """Mark the preset modified once the effect no longer matches what it wrote."""
    if (entry.kind == C.KIND_SIM_FIRE and entry.sim_preset and not entry.sim_preset_modified
            and not busy(entry) and is_modified(entry)):
        entry["sim_preset_modified"] = True


def watch(scene, depsgraph=None):
    """Catch edits made in Blender's Physics panel, as well as in ours.  Compared with
    the stored snapshot, never with the current catalogue."""
    changed = ({u.id.original.as_pointer() for u in depsgraph.updates}
               if depsgraph is not None else None)
    for entry in getattr(scene, "fas_effects", ()):
        if entry.kind != C.KIND_SIM_FIRE or not entry.sim_preset or entry.sim_preset_modified:
            continue
        owned = [obj.as_pointer() for obj in (entry.primary, entry.emitter) if obj is not None]
        if changed is not None and not any(pointer in changed for pointer in owned):
            continue
        note_edit(entry)


def reset_cache():
    _decoded.cache_clear()


# --- Applying a preset ------------------------------------------------------------

def _reshape(entry, shape):
    from . import sim_fire
    domain, emitter = entry.primary, entry.emitter
    sim_fire.fill_box(domain.data, shape["domain_size"], shape["domain_centre_z"])
    if emitter is not None and emitter.type == "MESH":
        if shape["emitter_patches"]:
            sim_fire.fill_patches(emitter.data, shape["emitter_patches"])
        else:
            sim_fire.fill_disc(emitter.data, shape["emitter_radius"])
        emitter.location = (0.0, 0.0, shape["emitter_z"])
    if entry.light is not None:
        entry.light.location = (0.0, 0.0, shape["light_height"])


def _set_material(entry, material):
    from . import sim_fire
    node = sim_fire.volume_node(entry)
    if node is None:
        return
    node.inputs["Density"].default_value = material["density"]
    grey = material["colour"]
    node.inputs["Color"].default_value = (grey, grey, grey, 1.0)
    node.inputs["Blackbody Intensity"].default_value = material["blackbody"]
    _ramp, strength = sim_fire.flame_colour(entry)
    if strength is not None:
        strength.inputs[1].default_value = material["flame_colour"]


def _set_light(entry, light):
    from . import fire_light
    if entry.light is None or entry.light.type != "LIGHT":
        return
    data = entry.light.data
    data.shadow_soft_size = light["radius"]
    fire_light.set_energy(data, light["energy"], flicker=light["flicker"])
    fire_light.set_speed(data, light["speed"])


def apply(context, entry, preset_id):
    """Write a package onto a Simulated Fire, once.  The sliders go back to 1, Detail
    to the preset's, and the cache is cleared so the next play shows the new fire."""
    from . import sim_fire
    if entry.kind != C.KIND_SIM_FIRE:
        raise RuntimeError(NOT_SIMULATED)
    package = CATALOG.get(preset_id)
    if package is None:
        raise RuntimeError(CHOOSE)
    if not bpy.app.build_options.fluid:
        raise RuntimeError(sim_fire.NO_FLUID_HERE)
    domain, flow = sim_fire.domain_settings(entry), sim_fire.flow_settings(entry)
    if domain is None or flow is None or entry.primary.type != "MESH":
        raise RuntimeError(NO_DOMAIN)
    with applying(entry):
        _reshape(entry, package["shape"])
        for field, value in package["domain"].items():
            setattr(domain, field, value)
        for field, value in package["flow"].items():
            setattr(flow, field, value)
        _set_material(entry, package["material"])
        _set_light(entry, package["light"])
        entry.base_fuel = package["flow"]["fuel_amount"]
        entry.base_smoke = package["flow"]["density"]
        entry.base_density = package["material"]["density"]
        entry.base_energy = package["light"]["energy"]
        entry.flame_intensity = 1.0
        entry.smoke_amount = 1.0
        entry.light_strength = 1.0
        entry.detail = package["entry"]["detail"]
        domain.resolution_max = entry.detail
        entry.primary.update_tag()
        sim_fire.clear_cache(entry)
        entry.sim_preset_snapshot = json.dumps(snapshot(entry), sort_keys=True)
        entry.sim_preset = preset_id
        entry.sim_preset_label = package["label"]
        entry.sim_preset_choice = preset_id
        entry.sim_preset_modified = False


class FAS_OT_apply_sim_preset(bpy.types.Operator):
    bl_idname = "fas.apply_sim_preset"
    bl_label = "Apply Preset"
    bl_description = ("Replace this fire's simulation settings with the preset's. "
                      "Press play from the first frame to see the new fire")
    bl_options = {"REGISTER", "UNDO"}

    uuid: bpy.props.StringProperty(options={"HIDDEN", "SKIP_SAVE"})

    def execute(self, context):
        entry = next((e for e in context.scene.fas_effects if e.uuid == self.uuid), None)
        if entry is None:
            return {"CANCELLED"}
        apply(context, entry, entry.sim_preset_choice)
        self.report({"INFO"}, f"{entry.sim_preset_label} applied: press play from the first frame to see it")
        return {"FINISHED"}


CLASSES = (FAS_OT_apply_sim_preset,)
