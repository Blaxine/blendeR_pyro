# SPDX-License-Identifier: GPL-3.0-or-later
"""Fire and Smoke from Mesh on a rigged character animated in place.

A 2 m cylinder is skinned to a two-bone armature: "Lower" stands still and "Upper"
swings from one side to the other.  Burning from the "Upper" group, the flames come
from the arm where it is now, and none from the lower part.  Every check that plays
steps one frame at a time from the first frame, since Replay only simulates forward.
"""

import math
import os
import sys

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fas_testlib as lib  # noqa: E402

import bpy  # noqa: E402
from fire_and_smoke.effects import sim_fire, sim_mesh_fire  # noqa: E402
from mathutils import Vector  # noqa: E402

PRESET = "SIMULATED_MESH_FIRE"
SWING = math.radians(60.0)
# The arm is out to one side at these frames, and out to the other.
ONE_SIDE, OTHER_SIDE = 24, 48
NEAR = 0.35         # metres from a bone's line
# The lower part, short of the joint, where the arm's own flames start.
LOWER_SHARE = 0.6
STATE = {}


def _cylinder(name, radius=0.15, height=2.0, rings=21, sides=12):
    verts, faces = [], []
    for ring in range(rings):
        z = height * ring / (rings - 1)
        for side in range(sides):
            angle = 2.0 * math.pi * side / sides
            verts.append((radius * math.cos(angle), radius * math.sin(angle), z))
    for ring in range(rings - 1):
        for side in range(sides):
            a, b = ring * sides + side, ring * sides + (side + 1) % sides
            faces.append((a, b, b + sides, a + sides))
    faces.append(tuple(range(sides - 1, -1, -1)))
    top = (rings - 1) * sides
    faces.append(tuple(range(top, top + sides)))
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(verts, [], faces)
    obj = bpy.data.objects.new(name, mesh)
    lib.scene().collection.objects.link(obj)
    lower = [i for i, v in enumerate(verts) if v[2] < height / 2 - 1e-6]
    upper = [i for i, v in enumerate(verts) if v[2] >= height / 2 - 1e-6]
    obj.vertex_groups.new(name="Lower").add(lower, 1.0, "REPLACE")
    obj.vertex_groups.new(name="Upper").add(upper, 1.0, "REPLACE")
    return obj


def _armature():
    data = bpy.data.armatures.new("Rig")
    rig = bpy.data.objects.new("Rig", data)
    lib.scene().collection.objects.link(rig)
    bpy.context.view_layer.objects.active = rig
    bpy.ops.object.mode_set(mode="EDIT")
    lower = data.edit_bones.new("Lower")
    lower.head, lower.tail = (0.0, 0.0, 0.0), (0.0, 0.0, 1.0)
    upper = data.edit_bones.new("Upper")
    upper.head, upper.tail = (0.0, 0.0, 1.0), (0.0, 0.0, 2.0)
    upper.parent = lower
    upper.use_connect = True
    bpy.ops.object.mode_set(mode="OBJECT")
    arm = rig.pose.bones["Upper"]
    arm.rotation_mode = "XYZ"
    for frame, angle in ((1, SWING), (ONE_SIDE, -SWING), (OTHER_SIDE, SWING)):
        # A bone's own Y runs along it: Z swings it sideways.
        arm.rotation_euler = (0.0, 0.0, angle)
        arm.keyframe_insert("rotation_euler", frame=frame)
    return rig


def _segment_distance(point, a, b):
    ab = b - a
    t = max(0.0, min(1.0, (point - a).dot(ab) / ab.length_squared))
    return (point - (a + ab * t)).length


def _bone_line(rig, name, share=1.0):
    bone = rig.pose.bones[name]
    head, tail = rig.matrix_world @ bone.head, rig.matrix_world @ bone.tail
    return head, head + (tail - head) * share


def _flame_near(entry, lines):
    """The share of the flame within NEAR of each line, and its total."""
    depsgraph = bpy.context.evaluated_depsgraph_get()
    settings = sim_fire.find_modifier(entry.primary.evaluated_get(depsgraph), "DOMAIN").domain_settings
    rx, ry, rz = settings.domain_resolution
    low, high = sim_mesh_fire.world_bounds(entry.primary)
    step = Vector(((high.x - low.x) / rx, (high.y - low.y) / ry, (high.z - low.z) / rz))
    total = 0.0
    near = [0.0] * len(lines)
    for index, value in enumerate(settings.flame_grid):
        if value <= 0.01:
            continue
        i, j, k = index % rx, (index // rx) % ry, index // (rx * ry)
        point = low + Vector(((i + 0.5) * step.x, (j + 0.5) * step.y, (k + 0.5) * step.z))
        total += value
        for n, (a, b) in enumerate(lines):
            if _segment_distance(point, a, b) <= NEAR:
                near[n] += value
    return [v / total if total else 0.0 for v in near], total


def test_setup():
    lib.clear_scene()
    scene = lib.scene()
    scene.frame_start, scene.frame_end = 1, 60
    scene.frame_set(1)
    body = _cylinder("Body")
    rig = _armature()
    deform = body.modifiers.new("Armature", "ARMATURE")
    deform.object = rig
    scene.frame_set(1)
    bpy.context.view_layer.objects.active = body
    body.select_set(True)
    STATE["body"], STATE["rig"] = body.name, rig.name
    result = bpy.ops.fas.effect_create(preset=PRESET)
    entry = scene.fas_effects[-1]
    STATE["uuid"] = entry.uuid
    lib.check("the rigged mesh is set on fire", result == {"FINISHED"} and entry.source == body)
    entry.burn_from_choice = "Upper"
    lib.check("burning from the arm's group", entry.burn_from == "Upper")
    copy = entry.emitter.evaluated_get(bpy.context.evaluated_depsgraph_get()).data
    tip = max(copy.vertices, key=lambda v: (entry.emitter.matrix_world @ v.co).z)
    lib.check("the copy is the posed mesh, not the rest pose", (entry.emitter.matrix_world @ tip.co).z < 1.8,
              f"{(entry.emitter.matrix_world @ tip.co).z:.2f}")


def test_the_flames_follow_the_arm():
    entry = next(e for e in lib.scene().fas_effects if e.uuid == STATE["uuid"])
    rig = bpy.data.objects[STATE["rig"]]
    scene = lib.scene()
    seen = {}
    for frame in range(1, OTHER_SIDE + 1):
        scene.frame_set(frame)
        if frame in (ONE_SIDE, OTHER_SIDE):
            seen[frame] = _bone_line(rig, "Upper")
            if frame == OTHER_SIDE:
                lines = (seen[OTHER_SIDE], seen[ONE_SIDE], _bone_line(rig, "Lower", LOWER_SHARE))
            else:
                # Where the arm will be: the mirror of where it is now.
                head, tail = seen[ONE_SIDE]
                mirror = (head, Vector((-tail.x, tail.y, tail.z)))
                lines = (seen[ONE_SIDE], mirror, _bone_line(rig, "Lower", LOWER_SHARE))
            (here, there, lower), total = _flame_near(entry, lines)
            side = "-x" if seen[frame][1].x < 0 else "+x"
            lib.info(f"frame {frame}, arm to {side}: {here:.0%} of the flame by the arm, {there:.0%} by where it "
                     f"was or will be, {lower:.0%} by the lower part (flame {total:.1f})")
            lib.check(f"frame {frame}: there's fire", total > 1.0, f"{total:.2f}")
            lib.check(f"frame {frame}: the flames are by the arm where it is now", here > 2.0 * there and here > 0.2,
                      f"{here:.2f} / {there:.2f}")
            lib.check(f"frame {frame}: none by the lower part", lower < 0.05, f"{lower:.3f}")
    lib.check("the arm was out to each side", seen[ONE_SIDE][1].x * seen[OTHER_SIDE][1].x < 0.0
              and min(abs(seen[ONE_SIDE][1].x), abs(seen[OTHER_SIDE][1].x)) > 0.5,
              f"{seen[ONE_SIDE][1].x:.2f} / {seen[OTHER_SIDE][1].x:.2f}")
    scene.frame_set(1)


def test_delete_cleans_up():
    bpy.ops.fas.effect_delete(uuid=STATE["uuid"])
    owned = [o.name for o in bpy.data.objects if lib.C.OWNER_PROP in o.keys()]
    body = bpy.data.objects.get(STATE["body"])
    lib.check("nothing owned is left", not owned, str(owned))
    lib.check("the character keeps its rig and groups", body is not None
              and [m.type for m in body.modifiers] == ["ARMATURE"]
              and [g.name for g in body.vertex_groups] == ["Lower", "Upper"])


lib.main(globals())
