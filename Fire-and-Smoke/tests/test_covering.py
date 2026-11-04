# SPDX-License-Identifier: GPL-3.0-or-later
"""A fire made inside one of the buyer's meshes, such as the default cube, is hidden in
every view: the add-on says which mesh is in the way, and never moves or hides it."""

import os
import sys

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fas_testlib as lib  # noqa: E402

import bpy  # noqa: E402
from fire_and_smoke.core import covering  # noqa: E402


def _cube(name="Cube", location=(0.0, 0.0, 0.0), size=2.0):
    bpy.ops.mesh.primitive_cube_add(size=size, location=location)
    cube = bpy.context.object
    cube.name = name
    return cube


def _fire(preset="SIMULATED_CAMPFIRE"):
    scene = lib.scene()
    scene.cursor.location = (0.0, 0.0, 0.0)
    result = bpy.ops.fas.effect_create(preset=preset)
    lib.check(f"{preset} creates", result == {"FINISHED"}, str(result))
    bpy.context.view_layer.update()
    return scene.fas_effects[-1]


def _hidden(entry):
    bpy.context.view_layer.update()
    return covering.covering(lib.scene(), entry)


def test_the_default_cube_hides_a_simulated_fire():
    lib.clear_scene()
    cube = _cube()
    entry = _fire()
    lib.check("the cube at the cursor is in the way", _hidden(entry) == ["Cube"], str(_hidden(entry)))
    lib.check("the message names it and says what to do",
              covering.sentence(["Cube"]) == "Cube is in the way and hides the fire: hide or move it")
    lib.check("the cube isn't changed", cube.visible_get() and tuple(cube.location) == (0.0, 0.0, 0.0)
              and lib.C.OWNER_PROP not in cube.keys())
    cube.hide_set(True)
    lib.check("a hidden cube isn't in the way", _hidden(entry) == [])
    cube.hide_set(False)
    cube.display_type = "WIRE"
    lib.check("nor a wireframe one", _hidden(entry) == [])
    cube.display_type = "TEXTURED"
    cube.location = (5.0, 0.0, 0.0)
    lib.check("nor one moved away", _hidden(entry) == [])
    entry.primary.location = (5.0, 0.0, 0.0)
    lib.check("but moving the fire into it is", _hidden(entry) == ["Cube"], str(_hidden(entry)))
    entry.primary.location = (5.0, 0.0, 0.6)
    lib.check("and a fire with its light above the cube still counts", _hidden(entry) == ["Cube"],
              str(_hidden(entry)))
    entry.primary.location = (0.0, 0.0, 0.0)
    cube.location = (0.0, 0.0, 0.0)
    cube.scale = (0.0, 1.0, 1.0)
    lib.check("a mesh scaled to nothing is skipped without an error", _hidden(entry) == [])
    cube.scale = (1.0, 1.0, 1.0)
    bpy.ops.fas.effect_delete(uuid=entry.uuid)


def test_what_never_counts():
    lib.clear_scene()
    bpy.ops.mesh.primitive_plane_add(size=20.0)
    lib.scene().objects[-1].name = "Ground"
    entry = _fire()
    lib.check("a ground plane under the fire isn't in the way", _hidden(entry) == [], str(_hidden(entry)))
    other = _fire()
    lib.check("nor is another fire's domain", _hidden(entry) == [] and _hidden(other) == [])
    bpy.ops.mesh.primitive_cube_add(size=6.0, location=(0.0, 0.0, 0.0))
    domain = bpy.context.object
    domain.name = "My Domain"
    domain.modifiers.new("Fluid", "FLUID").fluid_type = "DOMAIN"
    lib.check("nor the buyer's own fluid domain", _hidden(entry) == [], str(_hidden(entry)))
    for e in list(lib.scene().fas_effects):
        bpy.ops.fas.effect_delete(uuid=e.uuid)


def test_plane_fires_and_others():
    lib.clear_scene()
    _cube()
    entry = _fire("CAMPFIRE")
    lib.check("a plane Campfire inside the cube is hidden too", _hidden(entry) == ["Cube"], str(_hidden(entry)))
    bpy.ops.fas.effect_delete(uuid=entry.uuid)
    entry = _fire("THIN_SMOKE")
    lib.check("smoke rises out of it, so it isn't checked", _hidden(entry) == [])
    bpy.ops.fas.effect_delete(uuid=entry.uuid)
    cube = bpy.data.objects["Cube"]
    bpy.context.view_layer.objects.active = cube
    cube.select_set(True)
    entry = _fire("BURNING_OBJECT")
    lib.check("a burning mesh doesn't hide its own fire", _hidden(entry) == [], str(_hidden(entry)))
    bpy.ops.fas.effect_delete(uuid=entry.uuid)


def test_several_meshes():
    lib.clear_scene()
    for index, name in enumerate(("Box", "Crate", "Barrel", "Wall")):
        _cube(name, size=3.0 + index)
    entry = _fire()
    names = _hidden(entry)
    lib.check("every covering mesh is found", sorted(names) == ["Barrel", "Box", "Crate", "Wall"], str(names))
    lib.check("two are listed by name",
              covering.sentence(["Box", "Crate"]) == "Box and Crate are in the way and hide the fire: hide or move them")
    lib.check("more than three are counted",
              covering.sentence(["A", "B", "C", "D"]) == "A, B, C and 1 more are in the way and hide the fire: "
                                                          "hide or move them")
    lib.check("the panel's check stops on very large scenes",
              covering.covering(lib.scene(), entry, limit=2) == [])
    bpy.ops.fas.effect_delete(uuid=entry.uuid)


lib.main(globals())
