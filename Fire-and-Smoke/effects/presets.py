# SPDX-License-Identifier: GPL-3.0-or-later
"""The presets: plain data, applied once when an effect is created.

Saved scenes store a preset's number, so each number is fixed for good: a new preset
goes on the end of ``PRESETS`` with the next number.  ``DISPLAY_ORDER`` decides what the
panel shows, separately.
"""

import bpy

from .. import constants as C
from ..core import bounces, covering, delete
from . import creation, embers, flame_material, mesh_fire, sim_fire, sim_presets, smoke, smoke_material

FIRE_GROUP = "Fire"
SMOKE_GROUP = "Smoke"
EMBER_GROUP = "Embers"

# (id, number, label, description, icon, group)
PRESETS = (
    ("CANDLE", 0, "Candle", "A small steady flame for a candle or lamp", "LIGHT_POINT", FIRE_GROUP),
    ("TORCH", 1, "Torch", "A hand-held flame", "LIGHT_SPOT", FIRE_GROUP),
    ("CAMPFIRE", 2, "Campfire", "A fire about as tall as a person's waist", "LIGHT_AREA", FIRE_GROUP),
    ("BONFIRE", 3, "Bonfire", "A large fire taller than a person", "LIGHT_SUN", FIRE_GROUP),
    ("BURNING_OBJECT", 4, "Burning Object", "Set the selected mesh on fire, without changing it",
     "MESH_CUBE", FIRE_GROUP),
    ("THIN_SMOKE", 5, "Thin Smoke", "A pale drifting plume", "OUTLINER_DATA_VOLUME", SMOKE_GROUP),
    ("BLACK_SMOKE_COLUMN", 6, "Black Smoke Column", "A tall dark column for the distance",
     "OUTLINER_OB_VOLUME", SMOKE_GROUP),
    ("EMBERS", 7, "Embers", "Rising sparks. They replay from the start when you scrub",
     "PARTICLES", EMBER_GROUP),
    # Labelled Simulated Fire since it offers Normal Fire, Candle Fire and Campfire
    # (``sim_presets``).  Its id and number stay.
    ("SIMULATED_CAMPFIRE", 8, "Simulated Fire",
     "A real fire simulation: a campfire, a candle or a normal fire. It simulates as you play, "
     "so press play from the first frame",
     "MOD_FLUIDSIM", FIRE_GROUP),
)

DISPLAY_ORDER = ("CANDLE", "TORCH", "CAMPFIRE", "SIMULATED_CAMPFIRE", "BONFIRE", "BURNING_OBJECT",
                 "THIN_SMOKE", "BLACK_SMOKE_COLUMN", "EMBERS")

_BY_ID = {preset[0]: preset for preset in PRESETS}


def enum_items():
    """Display order, with each preset's fixed number."""
    return [(_BY_ID[i][0], _BY_ID[i][2], _BY_ID[i][3], _BY_ID[i][4], _BY_ID[i][1]) for i in DISPLAY_ORDER]


def label(preset_id):
    return _BY_ID[preset_id][2] if preset_id in _BY_ID else ""


def group(preset_id):
    return _BY_ID[preset_id][5]


def _fire(context, name, stack, light, location, **look):
    return creation.create_plane_effect(
        context, C.KIND_FIRE, name, flame_material.build_flame_material("FAS_Flame", **look), stack, location,
        glow=flame_material.build_glow_material("FAS_Glow"), light=light)


def create(context, preset_id, sim_preset=sim_presets.DEFAULT):
    """Build a preset at the 3D cursor; returns the effect's uuid.  ``sim_preset`` is the
    Simulated Fire's own preset."""
    location = context.scene.cursor.location
    if preset_id == "CANDLE":
        return _fire(context, "Candle",
                     {"Sites": 1, "Layers": 3, "Spread": 0.0, "Spacing": 0.002, "Width": 0.085,
                      "Height": 0.12, "Seed": 1},
                     {"energy": 1.6, "radius": 0.02, "flicker": 0.12, "speed": 5.0}, location,
                     speed=0.9, strength=1.2)
    if preset_id == "TORCH":
        return _fire(context, "Torch",
                     {"Sites": 3, "Layers": 3, "Spread": 0.03, "Spacing": 0.008, "Width": 0.24,
                      "Height": 0.55, "Seed": 2},
                     {"energy": 14.0, "radius": 0.07}, location, speed=1.25, strength=1.0)
    if preset_id == "CAMPFIRE":
        return _fire(context, "Campfire", dict(_campfire_stack()), dict(_campfire_light()), location)
    if preset_id == "BONFIRE":
        return _fire(context, "Bonfire",
                     {"Sites": 13, "Layers": 4, "Spread": 1.05, "Spacing": 0.14, "Width": 2.2,
                      "Height": 4.3, "Seed": 4},
                     {"energy": 900.0, "radius": 0.9}, location, speed=1.05, strength=0.65)
    if preset_id == "BURNING_OBJECT":
        return mesh_fire.create_mesh_fire(context, context.active_object)
    if preset_id == "THIN_SMOKE":
        return smoke.create_smoke(context, location)
    if preset_id == "BLACK_SMOKE_COLUMN":
        return smoke.create_smoke(context, location, C.KIND_COLUMN, "Smoke Column", smoke.COLUMN, smoke.COLUMN_LOOK)
    if preset_id == "EMBERS":
        return embers.create_embers(context, location)
    if preset_id == "SIMULATED_CAMPFIRE":
        return sim_fire.create_sim_fire(context, location, preset=sim_preset)
    raise RuntimeError(f"There's no preset called {preset_id}")


def _campfire_stack():
    from .campfire import CAMPFIRE
    return CAMPFIRE


def _campfire_light():
    from .campfire import CAMPFIRE_LIGHT
    return CAMPFIRE_LIGHT


class FAS_OT_effect_create(bpy.types.Operator):
    bl_idname = "fas.effect_create"
    bl_label = "Add Fire or Smoke"
    bl_description = "Add this preset at the 3D cursor"
    bl_options = {"REGISTER", "UNDO"}

    preset: bpy.props.EnumProperty(name="Preset", items=enum_items(), default="CAMPFIRE",
                                   options={"SKIP_SAVE"})
    sim_preset: bpy.props.EnumProperty(name="Simulation", items=sim_presets.ITEMS, default=sim_presets.DEFAULT,
                                       options={"SKIP_SAVE"},
                                       description="Which simulated fire to start from. "
                                                   "You can apply another one later")

    @classmethod
    def description(cls, _context, properties):
        return _BY_ID[properties.preset][3]

    def draw(self, _context):
        layout = self.layout
        layout.prop(self, "preset")
        if self.preset == "SIMULATED_CAMPFIRE":
            layout.prop(self, "sim_preset")

    @delete.guarded_create
    def execute(self, context):
        scene = context.scene
        cycles = getattr(scene, "cycles", None)
        limit = cycles.transparent_max_bounces if cycles is not None else None
        effect_uuid = create(context, self.preset, self.sim_preset)
        entry = next(e for e in scene.fas_effects if e.uuid == effect_uuid)
        entry.preset_id = self.preset
        if cycles is not None and cycles.transparent_max_bounces != limit:
            self.report({"INFO"}, f"Cycles transparent bounces raised to {cycles.transparent_max_bounces}, "
                                  "so the planes don't render black")
        if scene.camera is None:
            self.report({"WARNING"}, "This scene has no camera: add one before rendering")
        elif self.preset == "EMBERS":
            self.report({"INFO"}, "Press play from the first frame to see the embers")
        if self.preset == "SIMULATED_CAMPFIRE":
            self.report({"INFO"}, "Press play from the first frame to see the fire, in Rendered or Solid view")
        # New objects get their final positions on the next update.
        context.view_layer.update()
        hidden_by = covering.covering(scene, entry)
        if hidden_by:
            self.report({"WARNING"}, covering.sentence(hidden_by))
        return {"FINISHED"}


CLASSES = (FAS_OT_effect_create,)
