# SPDX-License-Identifier: GPL-3.0-or-later
"""Ordered panel controls, shared by drawing and headless contract checks.

``entry:`` IDs bind properties on the effect's entry; the others are named actions the
panel knows how to draw.  Advanced lists the complete view, including Simple controls.
"""
from .. import constants as C

# A simulated fire shows its whole list in both views, its preset first.
SIM_FIRE = ("sim_preset", "entry:detail", "entry:flame_intensity", "entry:smoke_amount", "entry:light_mode",
            "entry:light_strength")

SIMPLE = {
    C.KIND_FIRE: ("entry:size", "entry:brightness", "entry:light_mode", "entry:light_strength", "preview"),
    C.KIND_MESH_FIRE: ("entry:brightness", "entry:light_mode", "entry:light_strength", "preview"),
    C.KIND_SMOKE: ("entry:size", "entry:density", "preview"),
    C.KIND_COLUMN: ("entry:size", "entry:density", "preview"),
    C.KIND_EMBERS: ("entry:amount", "entry:ember_size"),
    C.KIND_SIM_FIRE: SIM_FIRE,
}
ADVANCED = {
    C.KIND_FIRE: ("entry:size", "entry:brightness", "entry:light_mode", "entry:light_strength", "preview",
                  "entry:layers", "entry:seed"),
    C.KIND_MESH_FIRE: ("entry:brightness", "entry:light_mode", "entry:light_strength", "preview",
                       "entry:layers", "entry:seed"),
    C.KIND_SMOKE: ("entry:size", "entry:density", "preview", "entry:layers", "entry:seed"),
    C.KIND_COLUMN: ("entry:size", "entry:density", "preview", "entry:layers", "entry:seed"),
    C.KIND_EMBERS: ("entry:amount", "entry:ember_size"),
    C.KIND_SIM_FIRE: SIM_FIRE,
}


def controls(kind, advanced=False):
    return (ADVANCED if advanced else SIMPLE).get(kind, ())
