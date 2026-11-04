# SPDX-License-Identifier: GPL-3.0-or-later
"""Fire and Smoke: fire and smoke from camera-facing planes for Blender.

Blender 4.2+ extension: name, version and requirements live in
blender_manifest.toml (the single source of the add-on version).
"""

import sys

import bpy
from bpy.props import CollectionProperty, IntProperty, PointerProperty

# Installing over a version that was loaded and then turned off in this Blender
# session re-runs only this file: its submodules would stay the old version's.
for _name in [n for n in sys.modules if n.startswith(__name__ + ".")]:
    del sys.modules[_name]
    globals().pop(_name[len(__name__) + 1:], None)

from . import constants as C
from .core import delete, errors, handlers, registry, view_sync
from .effects import campfire, embers, mesh_fire, presets, sim_presets, smoke, wind
from .ui import panel

_MODULES = (registry, errors, delete, campfire, smoke, mesh_fire, embers, presets, sim_presets, wind, panel)


def _all_classes():
    for mod in _MODULES:
        yield from getattr(mod, "CLASSES", ())


def register():
    # A previous failed enable can leave these exact Python classes registered.
    # Remove their handlers and properties before retrying.
    if any(cls.is_registered for cls in _all_classes()):
        unregister()
    try:
        _register()
    except Exception:
        unregister()
        raise


def _register():
    errors.register()
    for cls in _all_classes():
        if issubclass(cls, bpy.types.Operator):
            # No button may fail with a raw Python traceback.
            if not getattr(cls.execute, "_fas_guarded", False):
                cls.execute = errors.guard_operator(cls.execute)
                cls.execute._fas_guarded = True
        bpy.utils.register_class(cls)

    bpy.types.Scene.fas_effects = CollectionProperty(type=registry.FAS_EffectEntry)
    bpy.types.Scene.fas_view_target = PointerProperty(
        type=bpy.types.Object, name="View Target",
        description="The empty the planes face in Face Viewport")
    bpy.types.Scene.fas_bounce_original = IntProperty(default=-1)
    bpy.types.Scene.fas_bounce_set = IntProperty(default=-1)

    view_sync.register()
    handlers.register()


def unregister():
    # Also valid after partial registration: keep going if one resource fails.
    for module in (handlers, view_sync, errors):
        try:
            module.unregister()
        except Exception as exc:
            print(f"[{C.DISPLAY_NAME}] cleanup {module.__name__}: {exc}")

    for name in ("fas_bounce_set", "fas_bounce_original", "fas_view_target", "fas_effects"):
        if hasattr(bpy.types.Scene, name):
            try:
                delattr(bpy.types.Scene, name)
            except Exception as exc:
                print(f"[{C.DISPLAY_NAME}] cleanup Scene.{name}: {exc}")

    for cls in reversed(list(_all_classes())):
        if cls.is_registered:
            try:
                bpy.utils.unregister_class(cls)
            except Exception as exc:
                print(f"[{C.DISPLAY_NAME}] cleanup {cls.__name__}: {exc}")


if __name__ == "__main__":
    register()
