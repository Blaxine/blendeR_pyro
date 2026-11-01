# SPDX-License-Identifier: GPL-3.0-or-later
"""The record of each effect in ``Scene.fas_effects``.

Hold uuids, never entries, across removals: Python references into the collection
silently point at another entry afterwards.
"""

import bpy
from bpy.props import BoolProperty, EnumProperty, IntProperty, PointerProperty, StringProperty

from .. import constants as C
from ..effects import light_mode
from . import errors


def find_modifier(entry):
    """The effect's Geometry Nodes modifier, whatever it's been renamed to."""
    primary = entry.primary
    if primary is None:
        return None
    return next((m for m in primary.modifiers if m.type == "NODES" and m.node_group is not None
                 and C.OWNER_PROP in m.node_group.keys()), None)


@errors.guard_update("Fire and Smoke couldn't change the light")
def _light_mode_update(self, _context):
    if self.primary is not None:
        light_mode.apply(self.primary, self.light, self.light_mode)


@errors.guard_update("Fire and Smoke couldn't change which way the planes face")
def _face_viewport_update(self, _context):
    from ..effects import plane_stack
    modifier = find_modifier(self)
    if modifier is not None:
        plane_stack.set_inputs(modifier, {"Face Viewport": self.face_viewport})


class FAS_EffectEntry(bpy.types.PropertyGroup):
    uuid: StringProperty(name="ID")
    kind: StringProperty(name="Kind")
    preset_id: StringProperty(name="Preset")
    primary: PointerProperty(type=bpy.types.Object, name="Effect Object")
    light: PointerProperty(type=bpy.types.Object, name="Fire Light")
    source: PointerProperty(type=bpy.types.Object, name="Burning Mesh")
    instance: PointerProperty(type=bpy.types.Object, name="Ember Spark")
    root_collection: PointerProperty(type=bpy.types.Collection)
    planes: IntProperty(name="Planes", default=0, min=0)
    addon_version: StringProperty()
    data_version: IntProperty(default=C.DATA_VERSION)
    show_expanded: BoolProperty(name="Show", default=True)
    show_advanced: BoolProperty(name="More Settings", default=False)
    face_viewport: BoolProperty(
        name="Face Viewport", default=True, update=_face_viewport_update,
        description="Preview only: turn planes towards the 3D viewport as you orbit. "
                    "Final renders always face the scene camera")
    light_mode: EnumProperty(name="Light", items=light_mode.ITEMS, default=light_mode.REAL,
                             update=_light_mode_update)


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
