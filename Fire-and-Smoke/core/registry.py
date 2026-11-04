# SPDX-License-Identifier: GPL-3.0-or-later
"""The record of each effect in ``Scene.fas_effects``, and its adjustable settings.

Hold uuids, never entries, across removals: Python references into the collection
silently point at another entry afterwards.
"""

import bpy
from bpy.props import BoolProperty, EnumProperty, FloatProperty, IntProperty, PointerProperty, StringProperty

from .. import constants as C
from ..effects import light_mode
from . import errors

VIEWPORT = "VIEWPORT"
CAMERA = "CAMERA"
PREVIEW_ITEMS = (
    (VIEWPORT, "Face Viewport", "Preview only: turn planes towards the 3D viewport as you orbit. "
                                "Final renders always face the scene camera", 0),
    (CAMERA, "Face Camera", "Preview exactly what the scene camera will see", 1),
)


def find_modifier(entry):
    """The effect's Geometry Nodes modifier, whatever it's been renamed to."""
    primary = entry.primary
    if primary is None:
        return None
    return next((m for m in primary.modifiers if m.type == "NODES" and m.node_group is not None
                 and C.OWNER_PROP in m.node_group.keys()), None)


def _set_inputs(entry, values):
    from ..effects import plane_stack
    modifier = find_modifier(entry)
    if modifier is not None:
        plane_stack.set_inputs(modifier, values)
        entry.primary.update_tag()


def _materials(entry):
    """The effect's own materials, reached through its node tree."""
    modifier = find_modifier(entry)
    if modifier is None:
        return []
    return [node.inputs["Material"].default_value for node in modifier.node_group.nodes
            if node.bl_idname == "GeometryNodeSetMaterial" and node.inputs["Material"].default_value is not None]


def _set_material_value(entry, name, value):
    for material in _materials(entry):
        node = material.node_tree.nodes.get(name)
        if node is not None:
            node.outputs[0].default_value = value


@errors.guard_update("Fire and Smoke couldn't change the light")
def _light_mode_update(self, _context):
    if self.primary is not None:
        light_mode.apply(self.primary, self.light, self.light_mode)


@errors.guard_update("Fire and Smoke couldn't change which way the planes face")
def _preview_update(self, _context):
    _set_inputs(self, {"Face Viewport": self.preview_facing == VIEWPORT})


@errors.guard_update("Fire and Smoke couldn't change the size")
def _size_update(self, _context):
    _set_inputs(self, {"Width": self.base_width * self.size, "Height": self.base_height * self.size,
                       "Spread": self.base_spread * self.size, "Spacing": self.base_spacing * self.size})


@errors.guard_update("Fire and Smoke couldn't change the brightness")
def _brightness_update(self, _context):
    _set_material_value(self, "fas_strength", self.base_strength * self.brightness)


@errors.guard_update("Fire and Smoke couldn't change the density")
def _density_update(self, _context):
    _set_material_value(self, "fas_density", self.base_density * self.density)


@errors.guard_update("Fire and Smoke couldn't change the light")
def _light_strength_update(self, _context):
    from ..effects import fire_light
    if self.light is not None:
        fire_light.set_energy(self.light.data, self.base_energy * self.light_strength)


@errors.guard_update("Fire and Smoke couldn't change the variation")
def _seed_update(self, _context):
    _set_inputs(self, {"Seed": self.seed})


@errors.guard_update("Fire and Smoke couldn't change the layers")
def _layers_update(self, context):
    from . import bounces
    from ..effects import creation
    if find_modifier(self) is None:
        return
    _set_inputs(self, {"Layers": self.layers})
    self.planes = creation.plane_estimate(self.sites, self.layers, self.has_glow, self.source is not None)
    bounces.after_create(context.scene)


def _particle_settings(entry):
    primary = entry.primary
    return primary.particle_systems[0].settings if primary is not None and primary.particle_systems else None


@errors.guard_update("Fire and Smoke couldn't change the amount")
def _amount_update(self, _context):
    settings = _particle_settings(self)
    if settings is not None:
        settings.count = max(1, min(round(self.base_count * self.amount), C.MAX_EMBERS))


@errors.guard_update("Fire and Smoke couldn't change the ember size")
def _ember_size_update(self, _context):
    settings = _particle_settings(self)
    if settings is not None:
        settings.particle_size = self.base_ember_size * self.ember_size


class FAS_EffectEntry(bpy.types.PropertyGroup):
    uuid: StringProperty(name="ID")
    kind: StringProperty(name="Kind")
    preset_id: StringProperty(name="Preset")
    primary: PointerProperty(type=bpy.types.Object, name="Effect Object")
    light: PointerProperty(type=bpy.types.Object, name="Fire Light")
    source: PointerProperty(type=bpy.types.Object, name="Burning Mesh")
    instance: PointerProperty(type=bpy.types.Object, name="Ember Spark")
    emitter: PointerProperty(type=bpy.types.Object, name="Fire Emitter")
    root_collection: PointerProperty(type=bpy.types.Collection)
    planes: IntProperty(name="Planes", default=0, min=0)
    sites: IntProperty(default=0)
    has_glow: BoolProperty(default=False)
    addon_version: StringProperty()
    data_version: IntProperty(default=C.DATA_VERSION)
    show_expanded: BoolProperty(name="Show", default=True)
    show_advanced: BoolProperty(name="More Settings", default=False)

    # What the preset set: the sliders below scale these.
    base_width: FloatProperty(default=1.0)
    base_height: FloatProperty(default=1.0)
    base_spread: FloatProperty(default=0.0)
    base_spacing: FloatProperty(default=0.0)
    base_strength: FloatProperty(default=1.0)
    base_density: FloatProperty(default=1.0)
    base_energy: FloatProperty(default=1.0)
    base_count: IntProperty(default=1)
    base_ember_size: FloatProperty(default=0.01)

    preview_facing: EnumProperty(name="Viewport Preview", items=PREVIEW_ITEMS, default=VIEWPORT,
                                 update=_preview_update)
    light_mode: EnumProperty(name="Light", items=light_mode.ITEMS, default=light_mode.REAL,
                             update=_light_mode_update)
    size: FloatProperty(name="Size", default=1.0, min=0.05, soft_max=4.0, update=_size_update,
                        description="How big the effect is, compared with the preset")
    brightness: FloatProperty(name="Brightness", default=1.0, min=0.0, soft_max=3.0, update=_brightness_update,
                              description="How bright the flames look")
    density: FloatProperty(name="Density", default=1.0, min=0.0, soft_max=2.5, update=_density_update,
                           description="How thick the smoke is")
    light_strength: FloatProperty(name="Light Strength", default=1.0, min=0.0, soft_max=4.0,
                                  update=_light_strength_update,
                                  description="How strongly the fire's light lights the scene")
    amount: FloatProperty(name="Amount", default=1.0, min=0.01, soft_max=5.0, update=_amount_update,
                          description="How many embers, compared with the preset")
    ember_size: FloatProperty(name="Ember Size", default=1.0, min=0.05, soft_max=5.0, update=_ember_size_update,
                              description="How big each ember is, compared with the preset")
    layers: IntProperty(name="Layers", default=4, min=1, soft_max=12, update=_layers_update,
                        description="Planes in each stack. More is thicker and slower")
    seed: IntProperty(name="Variation", default=0, min=0, update=_seed_update,
                      description="A different random arrangement of the same look")


CLASSES = (FAS_EffectEntry,)


def entries(scene):
    return scene.fas_effects


def get(scene, effect_uuid):
    return next((e for e in scene.fas_effects if e.uuid == effect_uuid), None)


def add(scene, kind, effect_uuid, primary=None, root_collection=None):
    entry = scene.fas_effects.add()
    entry.uuid = effect_uuid
    entry.kind = kind
    entry.primary = primary
    entry.root_collection = root_collection
    entry.addon_version = C.ADDON_VERSION
    entry.data_version = C.DATA_VERSION
    return entry


def remove(scene, effect_uuid):
    for index, entry in enumerate(scene.fas_effects):
        if entry.uuid == effect_uuid:
            scene.fas_effects.remove(index)
            return True
    return False
