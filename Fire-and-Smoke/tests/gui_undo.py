# SPDX-License-Identifier: GPL-3.0-or-later
"""Undo in a real window, with operators run the way buttons run them.  Needs a window,
so it isn't part of the suite; it opens Blender, runs one sequence, reports and quits.

    blender --factory-startup --python tests/gui_undo.py -- plain

Sequences: plain, two, copy, linked, mesh, embers, and control (no add-on operators).
Never keep a Python reference to a Scene across an undo: it's stale afterwards, and
assigning it back to a window crashes Blender.
"""

import os
import sys

VARIANT = sys.argv[sys.argv.index("--") + 1]
sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.argv = [sys.argv[0], "--"]
import fas_testlib as lib  # noqa: E402,F401

import bpy  # noqa: E402

EXPECTED = {"plain": 1, "two": 1, "control": 0, "copy": 0, "linked": 1, "mesh": 1, "embers": 1}


def say(*a):
    print("UNDO", VARIANT, *a, flush=True)


def win():
    return bpy.context.window_manager.windows[0]


def count():
    return len(win().scene.fas_effects)


def click(op, *args, **kw):
    """Run an operator the way a button does, pushing its undo step."""
    with bpy.context.temp_override(window=win()):
        op("EXEC_DEFAULT", True, *args, **kw)


def undo():
    with bpy.context.temp_override(window=win()):
        bpy.ops.ed.undo()


def redo():
    with bpy.context.temp_override(window=win()):
        bpy.ops.ed.redo()


def first_uuid():
    return win().scene.fas_effects[0].uuid


SEQ = {
    "plain": [lambda: click(bpy.ops.fas.effect_create, preset="CAMPFIRE"),
              lambda: click(bpy.ops.fas.effect_delete, uuid=first_uuid()),
              undo, redo, undo, undo, redo],
    "two": [lambda: click(bpy.ops.fas.effect_create, preset="CAMPFIRE"),
            lambda: click(bpy.ops.fas.effect_create, preset="BONFIRE"),
            undo,
            lambda: click(bpy.ops.fas.effect_delete, uuid=first_uuid()),
            undo],
    "copy": [lambda: click(bpy.ops.fas.effect_create, preset="CAMPFIRE"),
             lambda: click(bpy.ops.scene.new, type="FULL_COPY"),
             lambda: click(bpy.ops.fas.effect_create, preset="BONFIRE"),
             undo,
             lambda: click(bpy.ops.fas.effect_delete, uuid=first_uuid()),
             undo, undo, undo],
    "control": [lambda: click(bpy.ops.mesh.primitive_cube_add),
                lambda: click(bpy.ops.scene.new, type="FULL_COPY"),
                lambda: click(bpy.ops.mesh.primitive_cube_add),
                undo,
                lambda: click(bpy.ops.object.delete),
                undo, undo, undo],
    "linked": [lambda: click(bpy.ops.fas.effect_create, preset="CAMPFIRE"),
               lambda: click(bpy.ops.scene.new, type="LINK_COPY"),
               lambda: click(bpy.ops.fas.effect_delete, uuid=first_uuid()),
               undo, undo],
    "mesh": [lambda: click(bpy.ops.fas.effect_create, preset="BURNING_OBJECT"),
             lambda: click(bpy.ops.fas.effect_delete, uuid=first_uuid()),
             undo, undo, redo],
    "embers": [lambda: click(bpy.ops.fas.effect_create, preset="EMBERS"),
               lambda: click(bpy.ops.fas.effect_delete, uuid=first_uuid()),
               undo, undo, redo],
}[VARIANT]
STEP = [0]


def run():
    if STEP[0] >= len(SEQ):
        say("PASS" if count() == EXPECTED[VARIANT] else "FAIL", "survived with", count(), "effects")
        bpy.ops.wm.quit_blender()
        return None
    index = STEP[0]
    STEP[0] += 1
    try:
        SEQ[index]()
    except Exception as exc:
        say("step", index, "error", str(exc)[:120])
    say("step", index, "effects", count())
    return 0.7


bpy.app.timers.register(run, first_interval=2.0)
