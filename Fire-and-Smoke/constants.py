# SPDX-License-Identifier: GPL-3.0-or-later
"""Fire and Smoke constants: name prefixes, kinds, user-facing strings."""

import os as _os

ADDON_NAME = "fire_and_smoke"

# The one place the product's display name lives.
DISPLAY_NAME = "Fire and Smoke"


def _manifest_version():
    """The add-on version: blender_manifest.toml is its single source."""
    try:
        import tomllib
        path = _os.path.join(_os.path.dirname(__file__), "blender_manifest.toml")
        with open(path, "rb") as fh:
            return str(tomllib.load(fh).get("version", "0.0.0"))
    except Exception:
        return "0.0.0"


ADDON_VERSION = _manifest_version()

# Instance attributes the materials read through Instancer-type Attribute nodes.
ATTR_LAYER = "fas_layer"
ATTR_RANDOM = "fas_random"
ATTR_TIME = "fas_time"
UV_ATTR = "UVMap"

# Cycles' hard maximum for transparent_max_bounces.
MAX_TRANSPARENT_BOUNCES = 1024
