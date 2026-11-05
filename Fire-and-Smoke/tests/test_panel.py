# SPDX-License-Identifier: GPL-3.0-or-later
"""The panel, drawn on a stand-in layout: headless Blender has no windows, so how it looks
goes on the release checklist, but what it says and offers is checked here."""

import os
import sys
from types import SimpleNamespace

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fas_testlib as lib  # noqa: E402

import bpy  # noqa: E402
from fire_and_smoke.effects import presets  # noqa: E402
from fire_and_smoke.ui import control_spec, panel  # noqa: E402


class StandIn:
    """Records what a panel draws."""

    def __init__(self, log=None):
        self.log = log if log is not None else {"labels": [], "props": [], "operators": []}

    def __getattr__(self, _name):
        return None

    def __setattr__(self, name, value):
        object.__setattr__(self, name, value)

    def _child(self, *_args, **_kwargs):
        return StandIn(self.log)

    row = column = box = split = grid_flow = _child

    def label(self, text="", **_kwargs):
        self.log["labels"].append(text)

    def prop(self, _data, name, **_kwargs):
        self.log["props"].append(name)

    def operator(self, idname, **_kwargs):
        self.log["operators"].append(idname)
        return SimpleNamespace()


def _draw(cls, active=None, shading=None):
    layout = StandIn()
    space = SimpleNamespace(shading=SimpleNamespace(type=shading)) if shading else None
    context = SimpleNamespace(scene=lib.scene(), active_object=active, space_data=space)
    cls.draw(SimpleNamespace(layout=layout), context)
    return layout.log


def _text(log):
    return " ".join(log["labels"])


def test_every_control_exists():
    properties = lib.addon.registry.FAS_EffectEntry.bl_rna.properties
    lib.check("every kind has controls", set(control_spec.SIMPLE) == set(lib.C.KIND_LABELS)
              and set(control_spec.ADVANCED) == set(lib.C.KIND_LABELS))
    for kind, simple in control_spec.SIMPLE.items():
        lib.check(f"{kind}: Simple is part of Advanced", set(simple) <= set(control_spec.ADVANCED[kind]))
        for token in control_spec.ADVANCED[kind]:
            if token.startswith("entry:"):
                lib.check(f"{kind}: {token} exists", token.split(":")[1] in properties)


def test_empty_state():
    lib.clear_scene()
    log = _draw(panel.FAS_PT_effects)
    lib.check("an empty panel says what to do", "Nothing here yet." in log["labels"])
    log = _draw(panel.FAS_PT_create)
    count = sum(1 for o in log["operators"] if o == "fas.effect_create")
    lib.check("all 10 presets are offered", count == 10, str(count))
    lib.check("Burning Object says it needs a mesh", "Select a mesh" in _text(log), _text(log))
    log = _draw(panel.FAS_PT_main)
    lib.check("no camera is explained", "no camera" in _text(log), _text(log))


def test_your_effects_comes_before_add():
    effects, create = panel.FAS_PT_effects, panel.FAS_PT_create
    lib.check("Your Effects is ordered above Add", effects.bl_order < create.bl_order,
              f"{effects.bl_order} / {create.bl_order}")
    order = list(panel.CLASSES)
    lib.check("and registered first", order.index(effects) < order.index(create))


def test_groups_follow_the_display_order():
    log = _draw(panel.FAS_PT_create)
    for group in (presets.FIRE_GROUP, presets.SMOKE_GROUP, presets.EMBER_GROUP):
        lib.check(f"the {group} group is shown", group in log["labels"])


def test_fire_box():
    lib.add_camera()
    bpy.ops.fas.effect_create(preset="CAMPFIRE")
    log = _draw(panel.FAS_PT_effects)
    lib.check("the preset's name is shown", "Campfire" in log["labels"])
    lib.check("Delete is offered", "fas.effect_delete" in log["operators"])
    lib.check("the facing switch is labelled preview-only", "Preview only:" in _text(log), _text(log))
    lib.check("and says what renders do", "final renders always face" in _text(log), _text(log))
    lib.check("Simple hides plane counts", "layers" not in log["props"])
    lib.check("the switch to more settings is offered", "show_advanced" in log["props"])
    entry = lib.scene().fas_effects[-1]
    entry.light_mode = "EMISSIVE"
    log = _draw(panel.FAS_PT_effects)
    lib.check("Emissive says it's Cycles-focused", "Cycles-focused" in _text(log), _text(log))
    entry.light_mode = "REAL"
    entry.show_advanced = True
    log = _draw(panel.FAS_PT_effects)
    lib.check("Advanced shows plane counts", "layers" in log["props"])
    log_main = _draw(panel.FAS_PT_main)
    lib.check("with a camera there's no warning", "no camera" not in _text(log_main))
    bpy.ops.fas.effect_delete(uuid=entry.uuid)


def test_embers_box():
    bpy.ops.fas.effect_create(preset="EMBERS")
    log = _draw(panel.FAS_PT_effects)
    lib.check("embers say they replay", "replay" in _text(log), _text(log))
    lib.check("and how to see them", "press play" in _text(log), _text(log))
    lib.check("embers have no facing switch", "preview_facing" not in log["props"])
    bpy.ops.fas.effect_delete(uuid=lib.scene().fas_effects[-1].uuid)


def test_sim_fire_box():
    bpy.ops.fas.effect_create(preset="SIMULATED_CAMPFIRE")
    log = _draw(panel.FAS_PT_effects)
    lib.check("the box is titled Simulated Fire", "Simulated Fire" in log["labels"], str(log["labels"]))
    lib.check("it says which simulation preset it started from", "Campfire" in log["labels"], str(log["labels"]))
    lib.check("with a Preset menu", "sim_preset_choice" in log["props"], str(log["props"]))
    lib.check("and an Apply button", "fas.apply_sim_preset" in log["operators"], str(log["operators"]))
    lib.check("the preset comes before the sliders",
              control_spec.controls(lib.C.KIND_SIM_FIRE)[0] == "sim_preset")
    lib.check("it says it simulates as you play", "simulates as you play" in _text(log), _text(log))
    lib.check("and to press play from the first frame", "press play from the first frame" in _text(log), _text(log))
    lib.check("and how to recover a frozen fire", "looks frozen" in _text(log), _text(log))
    lib.check("and that EEVEE shows a weaker look", "EEVEE shows a weaker look" in _text(log), _text(log))
    lib.check("and that Material Preview doesn't show it",
              "Material Preview doesn't show it: use Rendered or Solid view" in _text(log), _text(log))
    main = _draw(panel.FAS_PT_main, shading="MATERIAL")
    lib.check("in Material Preview the panel says to switch", "switch to Rendered or Solid" in _text(main),
              _text(main))
    main = _draw(panel.FAS_PT_main, shading="SOLID")
    lib.check("Solid view shows a simulated fire, so there's no Solid note for it alone",
              "Solid view only shows" not in _text(main) and "Material Preview doesn't" not in _text(main),
              _text(main))
    bpy.ops.mesh.primitive_cube_add(size=2.0, location=tuple(lib.scene().fas_effects[-1].primary.location))
    cube = bpy.context.object
    bpy.context.view_layer.update()
    log = _draw(panel.FAS_PT_effects)
    lib.check("a mesh hiding the fire is named in its box", f"{cube.name} is in the way" in _text(log), _text(log))
    bpy.data.objects.remove(cube)
    log = _draw(panel.FAS_PT_effects)
    lib.check("it has no facing switch", "preview_facing" not in log["props"])
    for name in ("detail", "flame_intensity", "smoke_amount", "light_mode", "light_strength"):
        lib.check(f"Simple view shows {name}", name in log["props"], str(log["props"]))
    lib.check("Detail says it gets slower", "Higher Detail is slower" in _text(log), _text(log))
    entry = lib.scene().fas_effects[-1]
    lib.check("Advanced shows the same list",
              control_spec.controls(entry.kind, True) == control_spec.controls(entry.kind, False))
    lib.check("so there's no switch to more settings", "show_advanced" not in log["props"])
    entry.flame_intensity = 1.5
    log = _draw(panel.FAS_PT_effects)
    lib.check("an edit marks the preset modified", "Campfire (modified)" in log["labels"], str(log["labels"]))
    entry.light_mode = "EMISSIVE"
    log = _draw(panel.FAS_PT_effects)
    lib.check("Emissive says it's Cycles-focused", "Cycles-focused" in _text(log), _text(log))
    original = panel.bpy
    fake = SimpleNamespace(app=SimpleNamespace(build_options=SimpleNamespace(fluid=False)), types=bpy.types)
    panel.bpy = fake
    try:
        log = _draw(panel.FAS_PT_effects)
    finally:
        panel.bpy = original
    lib.check("a Blender without Fluid is explained plainly", "built without Fluid" in _text(log), _text(log))
    bpy.ops.fas.effect_delete(uuid=lib.scene().fas_effects[-1].uuid)


def test_solid_view_is_explained():
    log = _draw(panel.FAS_PT_main, shading="SOLID")
    lib.check("no note with no effects", "Solid view" not in _text(log), _text(log))
    bpy.ops.fas.effect_create(preset="CAMPFIRE")
    log = _draw(panel.FAS_PT_main, shading="SOLID")
    lib.check("Solid view says how to see the effect", "Material Preview" in _text(log), _text(log))
    log = _draw(panel.FAS_PT_main, shading="MATERIAL")
    lib.check("Material Preview doesn't", "Solid view" not in _text(log), _text(log))
    bpy.ops.fas.effect_delete(uuid=lib.scene().fas_effects[-1].uuid)


def test_problems_are_plain():
    bpy.ops.mesh.primitive_cube_add()
    source = bpy.context.object
    bpy.ops.fas.effect_create(preset="BURNING_OBJECT")
    entry = lib.scene().fas_effects[-1]
    uuid = entry.uuid
    bpy.data.objects.remove(source)
    log = _draw(panel.FAS_PT_effects)
    lib.check("a missing mesh is explained", "mesh this fire was on is gone" in _text(log), _text(log))
    entry = lib.scene().fas_effects[-1]
    primary = entry.primary
    bpy.data.objects.remove(primary)
    log = _draw(panel.FAS_PT_effects)
    lib.check("a missing effect object is explained", "object is gone" in _text(log), _text(log))
    lib.check("and Delete is still there", "fas.effect_delete" in log["operators"])
    bpy.ops.fas.effect_delete(uuid=uuid)
    lib.check("Delete cleans it up", len(lib.scene().fas_effects) == 0)


def test_support_link_only_once_it_exists():
    log = _draw(panel.FAS_PT_main)
    if lib.C.SUPPORT_URL:
        lib.check("the link is offered", "wm.url_open" in log["operators"])
    else:
        lib.check("with no issues repo there's no link", "wm.url_open" not in log["operators"])
    original = panel.C.SUPPORT_URL
    panel.C.SUPPORT_URL = "https://example.com/issues"
    log = _draw(panel.FAS_PT_main)
    panel.C.SUPPORT_URL = original
    lib.check("setting the address is all it takes", "wm.url_open" in log["operators"])


def test_a_broken_box_doesnt_blank_the_panel():
    bpy.ops.fas.effect_create(preset="CAMPFIRE")
    original = control_spec.controls

    def explode(*_args):
        raise RuntimeError("Testing a broken box")

    panel.control_spec.controls = explode
    try:
        layout = StandIn()
        entry = lib.scene().fas_effects[-1]
        try:
            panel._draw_entry(layout, entry)
            lib.check("the box reports it", "This effect can't be displayed" in layout.log["labels"])
        except RuntimeError:
            # The foot of the box also reads the controls.
            lib.check("the box reports it", "This effect can't be displayed" in layout.log["labels"])
    finally:
        panel.control_spec.controls = original
    bpy.ops.fas.effect_delete(uuid=lib.scene().fas_effects[-1].uuid)


lib.main(globals())
