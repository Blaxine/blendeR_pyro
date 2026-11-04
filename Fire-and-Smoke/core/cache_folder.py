# SPDX-License-Identifier: GPL-3.0-or-later
"""Where a simulated effect keeps its cache.

Each effect has its own folder named after its uuid, inside a folder called
``fas_cache`` in Blender's session temp folder.
"""

import os

import bpy

from .. import constants as C


def path_for(effect_uuid):
    """The folder the path rule gives this effect now, as Blender stores it."""
    return os.path.join(bpy.app.tempdir, C.CACHE_FOLDER, effect_uuid)
