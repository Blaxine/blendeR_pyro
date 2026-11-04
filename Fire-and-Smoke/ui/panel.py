# SPDX-License-Identifier: GPL-3.0-or-later
"""The panel: pick a preset, adjust it, delete it, in plain words."""

import bpy

from .. import constants as C
from ..core import covering, errors, registry
from ..effects import light_mode, mesh_fire, presets, sim_fire, sim_presets
from . import control_spec

PREVIEW_NOTE = "Preview only: final renders always face the scene camera"
EMISSIVE_NOTE = "Emissive lighting is Cycles-focused"
EMBERS_NOTE = "Embers replay from the start: press play from the first frame to see them"
SIM_FIRE_NOTE = ("It simulates as you play: press play from the first frame. If the fire looks frozen, "
                 "go back to the first frame and play again")
SIM_EEVEE_NOTE = "EEVEE shows a weaker look than Cycles"
# Blender's Material Preview draws no fluid simulation, Quick Smoke's included.
SIM_VIEW_NOTE = "Material Preview doesn't show it: use Rendered or Solid view"
MATERIAL_PREVIEW_NOTE = ("Material Preview doesn't show the Simulated Fire: switch to Rendered or Solid "
                         "to see it")
DETAIL_NOTE = "Higher Detail is slower and uses more disk space"
SOLID_NOTE = "Solid view only shows rough shapes: switch to Material Preview or Rendered to see the effect"
NO_CAMERA_NOTE = "This scene has no camera: add one before rendering"


def _wrapped_label(layout, text, icon="NONE"):
    """Long notes as stacked lines, so a narrow sidebar doesn't cut them off."""
    column = layout.column(align=True)
    words, line = text.split(), ""
    lines = []
    for word in words:
        if len(line) + len(word) + 1 > 34:
            lines.append(line)
            line = word
        else:
            line = f"{line} {word}".strip()
    lines.append(line)
    for index, text_line in enumerate(lines):
        column.label(text=text_line, icon=icon if index == 0 else "BLANK1")


def entry_problem(entry):
    """What's wrong with this effect, as a sentence for the buyer, or None."""
    if entry.primary is None:
        return "This effect's object is gone. Delete it to clean up the rest"
    if entry.kind == C.KIND_SIM_FIRE and not bpy.app.build_options.fluid:
        return sim_fire.NO_FLUID_HERE
    if mesh_fire.is_missing_source(entry):
        return "The mesh this fire was on is gone. Delete the fire, then set a new mesh on fire"
    if entry.source is not None and len(entry.source.data.polygons) > mesh_fire.MAX_FACES:
        return "This mesh is now over the face limit, so scrubbing will be slow"
    return None


def _draw_sim_preset(layout, entry):
    """What was applied, and a menu with Apply for another: AquaSuite's preset row."""
    column = layout.column(align=True)
    text = entry.sim_preset_label or "Custom"
    if sim_presets.is_modified(entry):
        text += " (modified)"
    column.label(text=text, icon="PRESET")
    row = column.row(align=True)
    row.prop(entry, "sim_preset_choice", text="Preset")
    sub = row.row(align=True)
    sub.enabled = entry.sim_preset_choice != sim_presets.CUSTOM
    sub.operator("fas.apply_sim_preset", text="Apply").uuid = entry.uuid


def _draw_control(layout, entry, token):
    if token == "sim_preset":
        _draw_sim_preset(layout, entry)
    elif token == "preview":
        layout.prop(entry, "preview_facing", expand=True)
        _wrapped_label(layout, PREVIEW_NOTE, icon="INFO")
    elif token == "entry:light_mode":
        layout.prop(entry, "light_mode")
        if entry.light_mode != light_mode.REAL:
            _wrapped_label(layout, EMISSIVE_NOTE, icon="INFO")
    elif token == "entry:detail":
        layout.prop(entry, "detail")
        _wrapped_label(layout, DETAIL_NOTE, icon="INFO")
    elif token == "entry:light_strength":
        row = layout.row()
        row.enabled = entry.light_mode != light_mode.EMISSIVE
        row.prop(entry, "light_strength")
    elif token.startswith("entry:"):
        layout.prop(entry, token.split(":", 1)[1])


def _draw_entry(layout, entry):
    box = layout.box()
    header = box.row(align=True)
    header.prop(entry, "show_expanded", text="", emboss=False,
                icon="TRIA_DOWN" if entry.show_expanded else "TRIA_RIGHT")
    title = presets.label(entry.preset_id) or C.KIND_LABELS.get(entry.kind, entry.kind)
    header.label(text=title)
    operator = header.operator("fas.effect_delete", text="", icon="TRASH", emboss=False)
    operator.uuid = entry.uuid
    if not entry.show_expanded:
        return
    try:
        problem = entry_problem(entry)
        if problem:
            row = box.column()
            row.alert = True
            _wrapped_label(row, problem, icon="ERROR")
            if entry.primary is None:
                return
        hidden_by = covering.covering(entry.id_data, entry, limit=covering.MAX_CHECKED)
        if hidden_by:
            row = box.column()
            row.alert = True
            _wrapped_label(row, covering.sentence(hidden_by), icon="HIDE_ON")
        if entry.kind == C.KIND_EMBERS:
            _wrapped_label(box, EMBERS_NOTE, icon="INFO")
        elif entry.kind == C.KIND_SIM_FIRE:
            _wrapped_label(box, SIM_FIRE_NOTE, icon="INFO")
            _wrapped_label(box, SIM_VIEW_NOTE, icon="INFO")
            _wrapped_label(box, SIM_EEVEE_NOTE, icon="INFO")
        for token in control_spec.controls(entry.kind, entry.show_advanced):
            _draw_control(box, entry, token)
    except Exception as exc:
        row = box.row()
        row.alert = True
        row.label(text="This effect can't be displayed", icon="ERROR")
        errors.record("Fire and Smoke couldn't draw an effect", exc, kind=entry.kind, uuid=entry.uuid)
        errors.schedule()
    if control_spec.controls(entry.kind, True) != control_spec.controls(entry.kind, False):
        row = box.row()
        row.prop(entry, "show_advanced", emboss=False,
                 text="Fewer Settings" if entry.show_advanced else "More Settings",
                 icon="TRIA_UP" if entry.show_advanced else "TRIA_DOWN")


class FAS_PT_main(bpy.types.Panel):
    bl_label = C.DISPLAY_NAME
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = C.DISPLAY_NAME

    def draw(self, context):
        if context.scene.camera is None:
            row = self.layout.column()
            row.alert = True
            _wrapped_label(row, NO_CAMERA_NOTE, icon="ERROR")
        else:
            self.layout.label(text="Pick a preset below to start", icon="INFO")
        space = getattr(context, "space_data", None)
        shading = getattr(space, "shading", None)
        kinds = {entry.kind for entry in context.scene.fas_effects}
        # A simulated fire draws in Solid view, so the note is for the planes and embers.
        if kinds - {C.KIND_SIM_FIRE} and shading is not None and shading.type in {"SOLID", "WIREFRAME"}:
            _wrapped_label(self.layout, SOLID_NOTE, icon="SHADING_RENDERED")
        if C.KIND_SIM_FIRE in kinds and shading is not None and shading.type == "MATERIAL":
            row = self.layout.column()
            row.alert = True
            _wrapped_label(row, MATERIAL_PREVIEW_NOTE, icon="SHADING_RENDERED")
        if C.SUPPORT_URL:
            self.layout.operator("wm.url_open", text="Get Help", icon="HELP").url = C.SUPPORT_URL


class FAS_PT_create(bpy.types.Panel):
    bl_label = "Add"
    bl_order = 1
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = C.DISPLAY_NAME
    bl_parent_id = "FAS_PT_main"

    def draw(self, context):
        layout = self.layout
        shown = None
        column = None
        for item in presets.enum_items():
            preset_id, text, _description, icon, _number = item
            if presets.group(preset_id) != shown:
                shown = presets.group(preset_id)
                column = layout.column(align=True)
                column.label(text=shown)
            column.operator("fas.effect_create", text=text, icon=icon).preset = preset_id
        problem = mesh_fire.source_problem(context.active_object)
        if problem:
            row = layout.column()
            row.enabled = False
            _wrapped_label(row, f"Burning Object: {problem}", icon="INFO")


class FAS_PT_effects(bpy.types.Panel):
    bl_label = "Your Effects"
    # Above Add, so a new effect's settings show right where the buyer is looking,
    # not below nine preset buttons.
    bl_order = 0
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = C.DISPLAY_NAME
    bl_parent_id = "FAS_PT_main"

    def draw(self, context):
        layout = self.layout
        entries = registry.entries(context.scene)
        if not len(entries):
            column = layout.column(align=True)
            column.enabled = False
            column.label(text="Nothing here yet.", icon="INFO")
            column.label(text="Click a preset above.", icon="BLANK1")
            return
        for entry in entries:
            _draw_entry(layout, entry)


CLASSES = (FAS_PT_main, FAS_PT_effects, FAS_PT_create)
