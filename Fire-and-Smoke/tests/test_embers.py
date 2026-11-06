# SPDX-License-Identifier: GPL-3.0-or-later
"""Embers: rise, render in both engines, follow the timeline, and clean up."""

import os
import sys

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fas_testlib as lib  # noqa: E402

import bpy  # noqa: E402
from fire_and_smoke.core import copies, delete, handlers  # noqa: E402


def _settings(entry):
    return entry.primary.particle_systems[0].settings


def _tagged():
    groups = ("objects", "meshes", "materials", "particles", "collections")
    return [(g, i.name) for g in groups for i in getattr(bpy.data, g) if lib.C.OWNER_PROP in i.keys()]


def _alive(entry, frame):
    scene = lib.scene()
    for f in range(scene.frame_start, frame + 1):
        scene.frame_set(f)
    depsgraph = bpy.context.evaluated_depsgraph_get()
    system = entry.primary.evaluated_get(depsgraph).particle_systems[0]
    return [p for p in system.particles if p.alive_state == "ALIVE"]


def test_create():
    lib.clear_scene()
    lib.add_camera(location=(0.0, -6.0, 1.2), look_at=(0.0, 0.0, 1.2))
    lib.setup_render(width=320, height=180, background=(0.01, 0.01, 0.01))
    scene = lib.scene()
    scene.frame_start, scene.frame_end = 1, 100
    lib.check("created", bpy.ops.fas.embers_create() == {"FINISHED"})
    entry = scene.fas_effects[-1]
    lib.check("an embers entry", entry.kind == lib.C.KIND_EMBERS and entry.planes == 0)
    settings = _settings(entry)
    lib.check("runs for the whole timeline", (settings.frame_start, settings.frame_end) == (1.0, 100.0))
    lib.check("legacy particles rendered as an object", settings.render_type == "OBJECT"
              and settings.instance_object == entry.instance)
    spark = entry.instance
    lib.check("the spark isn't disabled in viewports, which stops them drawing its instances",
              not spark.hide_viewport)
    lib.check("the spark itself stays out of sight", spark.hide_get() and spark.hide_render)
    lib.check("revealing the spark is harmless: it's ember sized", max(spark.dimensions) < 0.1,
              str(spark.dimensions))


def test_they_rise():
    entry = lib.scene().fas_effects[-1]
    alive = _alive(entry, 40)
    lib.check("particles are alive by frame 40", len(alive) > 20, str(len(alive)))
    mean_z = sum(p.location.z for p in alive) / max(len(alive), 1)
    lib.check("and have risen", mean_z > 0.2, f"{mean_z:.2f}")


def test_render_in_both_engines():
    lib.scene().frame_set(40)

    def bright(pixels):
        return sum(1 for i in range(0, len(pixels), 4) if pixels[i] > 0.3)

    for label, engine in (("Cycles", "CYCLES"), ("EEVEE", lib.eevee_id())):
        pixels = lib.render(engine)
        lib.check(f"embers show in {label}", bright(pixels) >= 5, str(bright(pixels)))


def test_replays_the_same():
    entry = lib.scene().fas_effects[-1]
    first = sorted(round(p.location.z, 3) for p in _alive(entry, 30))
    lib.scene().frame_set(1)
    second = sorted(round(p.location.z, 3) for p in _alive(entry, 30))
    lib.check("playing again from the start gives the same embers", first == second,
              f"{len(first)} / {len(second)}")


def test_follow_the_timeline():
    scene = lib.scene()
    entry = scene.fas_effects[-1]
    count = _settings(entry).count
    handlers.note_ranges()
    scene.frame_end = 200
    handlers.follow_ranges()
    settings = _settings(entry)
    lib.check("the range follows", (settings.frame_start, settings.frame_end) == (1.0, 200.0),
              f"{settings.frame_start} {settings.frame_end}")
    lib.check("at the same rate", settings.count == count * 2, str(settings.count))
    lib.check("and Amount scales from the new total", scene.fas_effects[-1].base_count == count * 2)
    scene.frame_start, scene.frame_end = 150, 300
    handlers.follow_ranges()
    lib.check("also when the new range starts after the old one ends",
              (settings.frame_start, settings.frame_end) == (150.0, 300.0),
              f"{settings.frame_start} {settings.frame_end}")
    settings.frame_start, settings.frame_end = 160, 170
    handlers.note_ranges()
    scene.frame_end = 400
    handlers.follow_ranges()
    lib.check("a range I set stays mine", (settings.frame_start, settings.frame_end) == (160.0, 170.0))
    scene.frame_start, scene.frame_end = 1, 100


def test_readable_at_mid_ground_on_a_default_timeline():
    """The promise is mid-ground shots: a beginner's default 250-frame scene, camera 9 m away."""
    scene = lib.scene()
    scene.frame_start, scene.frame_end = 1, 250
    lib.add_camera(location=(0.0, -9.0, 1.4), look_at=(0.0, 0.0, 1.4))
    lib.setup_render(width=320, height=180, background=(0.01, 0.01, 0.01))
    bpy.ops.fas.effect_create(preset="EMBERS")
    entry = scene.fas_effects[-1]
    uuid = entry.uuid
    alive = _alive(entry, 60)
    lib.check("plenty are alive at once", len(alive) >= 80, str(len(alive)))
    pixels = lib.render(lib.eevee_id())
    bright = sum(1 for i in range(0, len(pixels), 4) if pixels[i] > 0.3)
    lib.info(f"{len(alive)} alive, {bright} bright pixels at 320x180, 9 m away")
    lib.check("they read at mid-ground", bright >= 150, f"{bright} bright pixels at 320x180")
    material = entry.instance.data.materials[0]
    r, g, b, a = material.diffuse_color
    lib.check("orange in Solid view, not grey", r > 0.8 and r > g * 2 and g > b and a == 1.0, str(tuple(material.diffuse_color)))

    # What a jump along the timeline shows, without playing from the start.
    scene.frame_set(1)
    scene.frame_set(120)
    depsgraph = bpy.context.evaluated_depsgraph_get()
    system = entry.primary.evaluated_get(depsgraph).particle_systems[0]
    lib.info(f"after jumping to frame 120: {sum(1 for p in system.particles if p.alive_state == 'ALIVE')} alive")
    bpy.ops.fas.effect_delete(uuid=uuid)
    scene.frame_start, scene.frame_end = 1, 100
    scene.frame_set(1)
    lib.add_camera(location=(0.0, -6.0, 1.2), look_at=(0.0, 0.0, 1.2))


def test_delete_cleans_up():
    uuid = lib.scene().fas_effects[-1].uuid
    bpy.ops.fas.effect_delete(uuid=uuid)
    lib.check("nothing tagged left", not _tagged(), str(_tagged()))


def test_full_copy_has_its_own_embers():
    scene = lib.scene()
    bpy.ops.fas.embers_create()
    source = bpy.context.window.scene
    before = set(bpy.data.scenes)
    bpy.ops.scene.new(type="FULL_COPY")
    copy_scene = next(iter(set(bpy.data.scenes) - before))
    bpy.context.window.scene = source
    copies.reidentify()
    original, copied = scene.fas_effects[-1], copy_scene.fas_effects[-1]
    lib.check("a new ID", original.uuid != copied.uuid)
    lib.check("its own settings", _settings(original) != _settings(copied))
    lib.check("spawning its own spark", _settings(copied).instance_object == copied.instance
              and copied.instance != original.instance)
    lib.check("whose spark can still draw in viewports", not copied.instance.hide_viewport)
    delete.delete_effect(scene, original.uuid)
    lib.check("the copy survives Delete in the original",
              _settings(copied).instance_object is not None and copied.primary is not None)
    delete.delete_effect(copy_scene, copied.uuid)
    bpy.data.scenes.remove(copy_scene)
    lib.check("nothing tagged left", not _tagged(), str(_tagged()))


lib.main(globals())
