# SPDX-License-Identifier: GPL-3.0-or-later
"""Fire and Smoke: fire and smoke from camera-facing planes for Blender.

Blender 4.2+ extension: name, version and requirements live in
blender_manifest.toml (the single source of the add-on version).
"""

import sys

import bpy

# Installing over a version that was loaded and then turned off in this Blender
# session re-runs only this file: its submodules would stay the old version's.
for _name in [n for n in sys.modules if n.startswith(__name__ + ".")]:
    del sys.modules[_name]
    globals().pop(_name[len(__name__) + 1:], None)

from . import constants as C
from .core import view_sync
from .effects import campfire

_MODULES = (campfire,)


def _all_classes():
    for mod in _MODULES:
        yield from getattr(mod, "CLASSES", ())


def register():
    # A previous failed enable can leave these exact Python classes registered.
    if any(cls.is_registered for cls in _all_classes()):
        unregister()
    try:
        _register()
    except Exception:
        unregister()
        raise


def _register():
    for cls in _all_classes():
        bpy.utils.register_class(cls)
    bpy.types.Scene.fas_view_target = bpy.props.PointerProperty(
        type=bpy.types.Object, name="View Target",
        description="The empty the planes face in Face Viewport")
    view_sync.register()


def unregister():
    try:
        view_sync.unregister()
    except Exception as exc:
        print(f"[{C.DISPLAY_NAME}] cleanup view sync: {exc}")
    if hasattr(bpy.types.Scene, "fas_view_target"):
        del bpy.types.Scene.fas_view_target
    for cls in reversed(list(_all_classes())):
        if cls.is_registered:
            try:
                bpy.utils.unregister_class(cls)
            except Exception as exc:
                print(f"[{C.DISPLAY_NAME}] cleanup {cls.__name__}: {exc}")


if __name__ == "__main__":
    register()
