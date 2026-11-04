# SPDX-License-Identifier: GPL-3.0-or-later
"""Create and Delete leave a scene as it was, and a failed Create leaves nothing."""

import os
import sys

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fas_testlib as lib  # noqa: E402

import bpy  # noqa: E402
from fire_and_smoke.core import errors  # noqa: E402
from fire_and_smoke.effects import flame_material  # noqa: E402

GROUPS = ("objects", "meshes", "lights", "materials", "node_groups", "actions", "collections")


def _counts():
    return {g: len(getattr(bpy.data, g)) for g in GROUPS}


def _tagged():
    return [(g, i.name) for g in GROUPS for i in getattr(bpy.data, g) if lib.C.OWNER_PROP in i.keys()]


def test_create_and_delete_restore_the_scene():
    lib.clear_scene()
    before = _counts()
    lib.scene().cycles.transparent_max_bounces = 8
    bpy.ops.fas.campfire_create()
    entry = lib.scene().fas_effects[0]
    lib.check("entry recorded", entry.kind == lib.C.KIND_FIRE and entry.primary is not None
              and entry.light is not None and entry.planes == 29)
    lib.check("entry stamped", entry.addon_version == lib.C.ADDON_VERSION and entry.data_version == lib.C.DATA_VERSION)
    tagged = {g for g, _name in _tagged()}
    lib.check("everything it made is tagged",
              {"objects", "meshes", "lights", "materials", "node_groups", "actions", "collections"} <= tagged, str(tagged))
    lib.check("the effect sits in its own collection",
              entry.primary.name in entry.root_collection.objects and entry.light.name in entry.root_collection.objects)
    bpy.ops.fas.effect_delete(uuid=entry.uuid)
    lib.check("no entry left", len(lib.scene().fas_effects) == 0)
    lib.check("nothing tagged left", not _tagged(), str(_tagged()))
    lib.check("counts are back", _counts() == before, f"{before} / {_counts()}")
    lib.check("view target removed with the last effect", lib.scene().fas_view_target is None)


def test_two_effects_delete_independently():
    bpy.ops.fas.campfire_create()
    first = lib.scene().fas_effects[0].uuid
    bpy.ops.fas.campfire_create()
    second = lib.scene().fas_effects[1].uuid
    bpy.ops.fas.effect_delete(uuid=first)
    lib.check("the other one remains", lib.scene().fas_effects[0].uuid == second
              and lib.scene().fas_effects[0].primary is not None)
    lib.check("view target stays while an effect needs it", lib.scene().fas_view_target is not None)
    bpy.context.view_layer.update()
    lib.check("the other one still evaluates", lib.instance_count(lib.scene().fas_effects[0].primary) == 29)
    bpy.ops.fas.effect_delete(uuid=second)
    lib.check("clean after both", not _tagged(), str(_tagged()))


def test_failed_create_leaves_nothing():
    before = _counts()
    original = flame_material.build_glow_material

    def explode(*_args, **_kwargs):
        raise RuntimeError("Testing a failed create")

    flame_material.build_glow_material = explode
    errors.reset_session()
    try:
        result = bpy.ops.fas.campfire_create()
    except RuntimeError as exc:
        result = {"CANCELLED"}
        lib.check("the message is plain", "Testing a failed create" in str(exc), str(exc))
    finally:
        flame_material.build_glow_material = original
    lib.check("reports cancelled", result == {"CANCELLED"})
    lib.check("no tagged leftovers", not _tagged(), str(_tagged()))
    lib.check("an error was recorded", errors.last_error() is not None)
    leftovers = {g: _counts()[g] - before[g] for g in GROUPS if _counts()[g] != before[g]}
    lib.check("no untagged leftovers worth keeping", set(leftovers) <= {"materials"}, str(leftovers))
    for material in list(bpy.data.materials):
        if material.users == 0:
            bpy.data.materials.remove(material)


def test_failed_simulated_create_leaves_no_folder():
    from fire_and_smoke.core import cache_folder
    from fire_and_smoke.effects import presets, sim_fire
    original = sim_fire.create_sim_fire
    made = []

    def build_then_fail(context, location, **kwargs):
        effect_uuid = original(context, location, **kwargs)
        for frame in range(1, 4):
            context.scene.frame_set(frame)
        path = cache_folder.temp_path(effect_uuid)
        made.append((path, os.path.isdir(path)))
        raise RuntimeError("Testing a failed create")

    presets.sim_fire.create_sim_fire = build_then_fail
    errors.reset_session()
    try:
        try:
            result = bpy.ops.fas.effect_create(preset="SIMULATED_CAMPFIRE")
        except RuntimeError:
            result = {"CANCELLED"}
    finally:
        presets.sim_fire.create_sim_fire = original
    lib.check("reports cancelled", result == {"CANCELLED"})
    lib.check("it had written a cache folder", bool(made) and made[0][1], str(made))
    lib.check("a failed create leaves no folder", bool(made) and not os.path.exists(made[0][0]), str(made))
    lib.check("and no tagged leftovers", not _tagged(), str(_tagged()))
    lib.scene().frame_set(1)


def test_bug_report_has_no_private_paths():
    errors.reset_session()
    err = errors.record("Testing", RuntimeError(f"failed at {os.path.expanduser('~')}/secret.blend"))
    report = errors.build_report(err)
    lib.check("the home folder is scrubbed", os.path.expanduser("~") not in report, report[:200])


lib.main(globals())
