# SPDX-License-Identifier: GPL-3.0-or-later
"""Wind: an owned Wind force field that blows the Simulated Fire, with Power, Gusts and
Direction in its box, and that makes every simulated fire simulate again when it changes."""

import math
import os
import sys
import tempfile

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fas_testlib as lib  # noqa: E402

import bpy  # noqa: E402
from fire_and_smoke.effects import sim_fire, wind  # noqa: E402
from fire_and_smoke.ui import control_spec  # noqa: E402
from mathutils import Vector  # noqa: E402

STATE = {}


def _entries(kind):
    return [e for e in lib.scene().fas_effects if e.kind == kind]


def _wind():
    return _entries(lib.C.KIND_WIND)[-1]


def _play(to):
    scene = lib.scene()
    for frame in range(scene.frame_start, to + 1):
        scene.frame_set(frame)


def _centre(entry):
    """Where the smoke and flames are, across the domain: 0.5 is the middle."""
    depsgraph = bpy.context.evaluated_depsgraph_get()
    settings = sim_fire.find_modifier(entry.primary.evaluated_get(depsgraph), "DOMAIN").domain_settings
    grid = list(settings.density_grid)
    rx, ry, _rz = settings.domain_resolution
    total = max(sum(grid), 1e-6)
    x = sum(d * (i % rx) for i, d in enumerate(grid)) / total / rx
    y = sum(d * ((i // rx) % ry) for i, d in enumerate(grid)) / total / ry
    return x, y


class _Clears:
    """Counts the simulated fires whose cache was cleared."""

    def __enter__(self):
        self.cleared = []
        self.original = sim_fire.clear_cache
        sim_fire.clear_cache = lambda entry: (self.cleared.append(entry.uuid), self.original(entry))
        return self

    def __exit__(self, *_args):
        sim_fire.clear_cache = self.original


def test_create():
    lib.clear_scene()
    lib.add_camera()
    scene = lib.scene()
    scene.cursor.location = (1.0, 2.0, 0.0)
    bpy.ops.mesh.primitive_cube_add(location=(8.0, 0.0, 0.0))
    mine = bpy.context.object
    mine.select_set(True)
    bpy.context.view_layer.objects.active = mine
    result = bpy.ops.fas.wind_create()
    lib.check("Wind creates", result == {"FINISHED"}, str(result))
    entry = _wind()
    obj = entry.primary
    lib.check("it's a Wind force field", obj is not None and obj.field is not None and obj.field.type == "WIND")
    lib.check("blowing the same way everywhere in front of it", obj.field.shape == "PLANE")
    lib.check("owned by the add-on", lib.C.OWNER_PROP in obj.keys()
              and lib.C.OWNER_PROP in entry.root_collection.keys())
    lib.check("starts as a light breeze", abs(obj.field.strength - 0.1) < 1e-6 and abs(entry.wind_power - 0.4) < 1e-6,
              f"{obj.field.strength}")
    lib.check("with some gusts", abs(obj.field.noise - wind.DEFAULT_GUSTS * wind.NOISE_PER_GUST) < 1e-6)
    lib.check("upwind of the 3D cursor, blowing towards it",
              (obj.location - Vector((1.0 - wind.UPWIND, 2.0, wind.HEIGHT))).length < 1e-5,
              str(tuple(obj.location)))
    blow = obj.matrix_world.to_3x3() @ Vector((0.0, 0.0, 1.0))
    lib.check("its field points along +X", (blow - Vector((1.0, 0.0, 0.0))).length < 1e-5, str(blow))
    lib.check("the buyer's selection is unchanged",
              bpy.context.view_layer.objects.active == mine and mine.select_get() and not obj.select_get())
    lib.check("the panel shows Power, Gusts and Direction",
              control_spec.controls(lib.C.KIND_WIND) == ("entry:wind_power", "entry:wind_gusts",
                                                           "entry:wind_direction"))
    bpy.data.objects.remove(mine)


def test_sliders():
    entry = _wind()
    obj = entry.primary
    entry.wind_power = 1.0
    lib.check("Power 1 is a strong breeze", abs(obj.field.strength - wind.STRENGTH_PER_POWER) < 1e-6)
    entry.wind_power = 0.0
    lib.check("Power 0 is still air", obj.field.strength == 0.0)
    entry.wind_gusts = 1.0
    lib.check("Gusts set the field's noise", abs(obj.field.noise - wind.NOISE_PER_GUST) < 1e-6)
    entry.wind_direction = math.radians(90.0)
    bpy.context.view_layer.update()
    blow = obj.matrix_world.to_3x3() @ Vector((0.0, 0.0, 1.0))
    lib.check("Direction turns it to blow along +Y", (blow - Vector((0.0, 1.0, 0.0))).length < 1e-5,
              str(blow))
    lib.check("and keeps it upwind of the same spot",
              (obj.location - Vector((1.0, 2.0 - wind.UPWIND, wind.HEIGHT))).length < 1e-5,
              str(tuple(obj.location)))
    bpy.ops.fas.effect_delete(uuid=entry.uuid)


def test_wind_blows_the_fire():
    lib.clear_scene()
    lib.add_camera()
    scene = lib.scene()
    scene.cursor.location = (0.0, 0.0, 0.0)
    scene.frame_start, scene.frame_end = 1, 60
    scene.frame_set(1)
    bpy.ops.fas.effect_create(preset="SIMULATED_CAMPFIRE")
    fire = _entries(lib.C.KIND_SIM_FIRE)[-1]
    _play(40)
    calm = _centre(fire)
    scene.frame_set(1)
    with _Clears() as clears:
        bpy.ops.fas.wind_create()
    lib.check("adding wind makes the fire simulate again", fire.uuid in clears.cleared)
    entry = _wind()
    with _Clears() as clears:
        entry.wind_power = 1.0
    lib.check("so does changing its power", fire.uuid in clears.cleared)
    _play(40)
    windy = _centre(fire)
    lib.info(f"plume across the domain after 40 frames: calm x {calm[0]:.3f}, power 1 x {windy[0]:.3f}")
    # Its logs are uneven, so a calm fire leans a little either way.
    lib.check("with no wind the fire rises roughly straight", abs(calm[0] - 0.5) < 0.1, f"{calm[0]:.3f}")
    lib.check("wind blows it downwind", windy[0] > calm[0] + 0.08, f"{calm[0]:.3f} -> {windy[0]:.3f}")
    scene.frame_set(1)
    with _Clears() as clears:
        entry.wind_direction = math.radians(90.0)
    lib.check("turning it makes the fire simulate again", fire.uuid in clears.cleared)
    _play(40)
    turned = _centre(fire)
    lib.check("and blows it the new way", turned[1] > calm[1] + 0.08 and abs(turned[0] - calm[0]) < 0.06,
              f"{calm} -> {turned}")
    scene.frame_set(1)
    STATE["fire"] = fire.uuid


def test_saved_and_deleted():
    path = os.path.join(tempfile.mkdtemp(prefix="fas_wind_"), "wind.blend")
    bpy.ops.wm.save_as_mainfile(filepath=path)
    bpy.ops.wm.open_mainfile(filepath=path)
    entry = _wind()
    lib.check("the wind is saved", entry.primary is not None and entry.primary.field.type == "WIND"
              and abs(entry.primary.field.strength - wind.STRENGTH_PER_POWER) < 1e-6)
    tagged_before = [o.name for o in bpy.data.objects if lib.C.OWNER_PROP in o.keys()]
    with _Clears() as clears:
        result = bpy.ops.fas.effect_delete(uuid=entry.uuid)
    lib.check("Delete removes the wind", result == {"FINISHED"} and not _entries(lib.C.KIND_WIND)
              and len([o for o in bpy.data.objects if lib.C.OWNER_PROP in o.keys()]) == len(tagged_before) - 1)
    lib.check("and the fire simulates again without it", STATE["fire"] in clears.cleared)
    lib.check("the fire stays", len(_entries(lib.C.KIND_SIM_FIRE)) == 1)


lib.main(globals())
