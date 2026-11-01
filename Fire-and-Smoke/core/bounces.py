# SPDX-License-Identifier: GPL-3.0-or-later
"""The bounce limit: the scene's Cycles transparent bounces, as the add-on manages it.

A ray that crosses as many transparent surfaces as the limit draws solid black, so a
scene needs a limit above the total planes of its effects.  The scene records its
original value and the value set, and the limit only comes back down while it still
equals the value set: a limit the buyer changed is theirs.
"""

from .. import constants as C

RAISED = "RAISED"
RESTORED = "RESTORED"
LOWERED = "LOWERED"
LEFT_ALONE = "LEFT_ALONE"


def _cycles(scene):
    return getattr(scene, "cycles", None)


def total_planes(scene):
    return sum(entry.planes for entry in scene.fas_effects)


def _clamped(value):
    return min(value, C.MAX_TRANSPARENT_BOUNCES)


def after_create(scene):
    """Raise the limit if the scene's planes reach it.  Returns the new value or None."""
    cycles = _cycles(scene)
    total = total_planes(scene)
    if cycles is None or cycles.transparent_max_bounces > total:
        return None
    if scene.fas_bounce_original < 0 or scene.fas_bounce_set != cycles.transparent_max_bounces:
        # Nothing recorded, or the buyer changed it since: this value is the new original.
        scene.fas_bounce_original = cycles.transparent_max_bounces
    scene.fas_bounce_set = _clamped(total + 1)
    cycles.transparent_max_bounces = scene.fas_bounce_set
    return scene.fas_bounce_set


def after_delete(scene):
    """Bring the limit back down if it's still ours.  Returns (outcome, value) or None."""
    cycles = _cycles(scene)
    if cycles is None or scene.fas_bounce_original < 0:
        return None
    original = scene.fas_bounce_original
    if cycles.transparent_max_bounces != scene.fas_bounce_set:
        scene.fas_bounce_original = -1
        scene.fas_bounce_set = -1
        return LEFT_ALONE, cycles.transparent_max_bounces
    total = total_planes(scene)
    if not len(scene.fas_effects) or original > total:
        cycles.transparent_max_bounces = original
        scene.fas_bounce_original = -1
        scene.fas_bounce_set = -1
        return RESTORED, original
    wanted = _clamped(total + 1)
    if wanted < cycles.transparent_max_bounces:
        cycles.transparent_max_bounces = wanted
        scene.fas_bounce_set = wanted
        return LOWERED, wanted
    return None


def describe(outcome):
    """A sentence for the status bar, or None."""
    if outcome is None:
        return None
    what, value = outcome
    if what == RESTORED:
        return f"Cycles transparent bounces restored to {value}"
    if what == LOWERED:
        return f"Cycles transparent bounces lowered to {value}"
    if what == LEFT_ALONE:
        return f"Cycles transparent bounces left at {value}, since it has changed"
    return None
