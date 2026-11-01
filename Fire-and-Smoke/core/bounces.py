# SPDX-License-Identifier: GPL-3.0-or-later
"""The Cycles transparent bounce limit.

A ray that crosses as many transparent surfaces as the limit draws solid black,
so a scene needs a limit above the number of planes it holds.
"""

from .. import constants as C


def _cycles(scene):
    return getattr(scene, "cycles", None)


def raise_for(scene, planes):
    """Raise the limit above ``planes`` when needed; return the new value or None."""
    cycles = _cycles(scene)
    if cycles is None or cycles.transparent_max_bounces > planes:
        return None
    cycles.transparent_max_bounces = min(planes + 1, C.MAX_TRANSPARENT_BOUNCES)
    return cycles.transparent_max_bounces
