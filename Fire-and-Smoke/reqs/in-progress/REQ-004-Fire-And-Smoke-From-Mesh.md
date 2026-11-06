# REQ-004 — Fire and Smoke from Mesh

| Field | Value |
| ----- | ----- |
| ID | REQ-004 |
| Title | Fire and Smoke from Mesh |
| SOLVE | — |
| Status | InProgress |
| Phase | Feature on REQ-003's Simulated Fire, pre-1.0 |
| Tier | Feature |
| Area | One new effect kind: a Mantaflow fire that burns from the buyer's mesh, its Burn From setting, the shared simulated-fire code paths, panel, presets, release gate, docs |
| Author | Blaxine |
| Created | 2026-11-05 |
| Last Updated | 2026-11-06 |

> Grilled in conversation on 2026-11-05, with no PRD. It builds on REQ-002's Simulated Fire and REQ-003's presets and sliders, and changes REQ-001's preset and eye-check counts again: 10 presets, 40 eye checks. See Dependencies.

> Status on 2026-11-06: all seven slices are built, and every criterion below is verified on 4.5.4 and 5.2.2, with the owner's verdicts on the sizes and the character. Still open: 5.1, which isn't installed (Q14), and the release checklist's eye checks for this preset, which are the owner's.

## Short Description

A tenth preset, **Fire and Smoke from Mesh**, for the add-on's beginners. Select any mesh, click, and it burns with a real Mantaflow fire and smoke that has every Simulated Fire control: the simulation presets, Detail, Flame Intensity, Flame Noise, Smoke Amount, the look sliders, the light and wind. Fire comes from the whole mesh, or, with **Burn From**, only from one of its vertex groups, with painted weights setting how strongly each part burns. The buyer's mesh is never changed: the add-on's own hidden emitter reads it live, so the fire follows it as it's moved, edited or animated in place. The buyer's mesh stays visible and burns.

## Constraints

Measured on Blender 4.5.4 and 5.2.2 on this PC on 2026-11-05, headless, with a Geometry Nodes Object Info copy (Relative) of the buyer's mesh as the emitter and surface emission. 5.1 isn't installed here.

- **A flow's vertex group is an index, not a name.** `FluidFlowSettings.density_vertex_group` only accepts a name on the emitter object's own vertex group list, stores its position, and reads that position in the evaluated mesh's weights. Those weights carry the buyer's list. On a 2 × 1 m grid with "Left" at position 1 of the buyer's ["Other", "Left"], an emitter whose own list was just ["Left"] burned evenly and weakly (left 511.7, right 510.4). The control, the flow on the buyer's mesh, burned 2724.8 left and 3.7 right.
- **A mirrored list matches the control exactly.** With the emitter's list holding the buyer's names in the buyer's order, the same grid burned 2724.8 left and 3.7 right on 5.2, and 2816.8 and 8.3 on 4.5, the same as the control. A Store Named Attribute into a group of the emitter's own changed nothing: it still read position 0.
- **Muting the flow's Fluid modifier in viewport and render stops all emission**: a flame sum of 0 after 24 frames, on both versions.
- **The same values don't give the same-looking fire at every size.** Campfire domain values on a cube of edge *s*, in a box 2.2 *s* wide and 4 *s* tall from the ground, at 64 divisions, after 40 frames, flame top as a share of the box (the cube's top is at 0.25): 0.5 m 0.97, 2 m 0.48, 8 m 0.39 on 5.2; 0.97, 0.69 and 0.64 on 4.5. Time scale hardly changes it: 8 m at 0.5 gave 0.34 on 5.2.
- **Cost per frame for those boxes**, frames 21 to 40, headless: 0.5 m ≈ 96 ms, 2 m ≈ 52 ms, 8 m ≈ 49 ms on 5.2; 103, 101 and 83 ms on 4.5.
- **4.5 and 5.2 simulate the same mesh fire differently**: on the 2 m cube, flame sums of 12398 on 4.5 and 5538 on 5.2. The look is tuned on 5.2 and checked on 4.5 by render.
- **A box that follows the mesh carries its fire.** A 1 m cube moved 1.5 m over 30 frames, with the domain's Copy Location (offset) on the cube: the flame centre ended at 1.51 m on both versions. A box that stayed put left it at 0.87 m (5.2) and 0.79 m (4.5), cut off at the edge.
- **Delete keeps an owned object that isn't parented to the primary.** `delete._adopted` treats it as the buyer's, so the emitter and light must be the domain's children.
- **Simulated-fire behaviour is gated on `entry.kind == C.KIND_SIM_FIRE` in many places**: `core/cache_folder.py` (`simulated`), `effects/wind.py` (`simulations_changed`), `effects/sim_presets.py` (`note_edit`, `watch`, `apply`), `ui/panel.py` (`entry_problem`, the box notes, the Material Preview and Solid notes), and `core/covering.py` (`FIRE_KINDS`, `_points`). `mesh_fire.is_missing_source` checks only `KIND_MESH_FIRE`.
- **The mesh rules already exist.** `mesh_fire.source_problem` refuses a non-mesh, one of an effect's own parts, a mesh with no faces, and more than 2,000,000 faces. `WARN_FACES` is 500,000.

## Architectural decisions

- **Identity:** a new effect kind `SIM_MESH_FIRE`, labelled "Fire and Smoke from Mesh". A new preset `SIMULATED_MESH_FIRE`, fixed number 9, labelled "Fire and Smoke from Mesh", in the Fire group, displayed straight after Burning Object.
- **Simulated kinds:** the constants name both simulated kinds together, and every check that means "a simulation" uses that group, not `KIND_SIM_FIRE` alone.
- **The buyer's mesh is never changed:** no modifier, constraint, tag, vertex group or visibility change, by Create, any control, Apply or Delete. Its object is the entry's `source`.
- **Emitter:** an owned object with an empty mesh of its own. Its Geometry Nodes modifier outputs the source's evaluated mesh through Object Info in Relative space, with the source given as a modifier input. Its Fluid flow follows: Smoke & Fire, Inflow, mesh source, surface emission. It's hidden from renders and drawn as wire.
- **Vertex group mirror:** the emitter's own vertex group list always holds the source's group names in the source's order. It's synced at Create, whenever Burn From changes, and whenever the source's list changes. It's written only when it differs.
- **Burn From:** stored by group name on the entry, never by position. Empty means Whole Mesh, the default. A chosen name sets the flow's vertex group, and weights set emission strength. A change clears the Replay cache.
- **A missing group or source stops the fire:** the flow's Fluid modifier is muted in viewport and render until the group or mesh is back, and the box says why. The fire never falls back to the whole mesh.
- **Domain:** the effect's primary, sized once at Create around the source's world bounds, with headroom for flames above and room for movement around it. It follows the source with Copy Location (offset) only, never rotation or scale. The emitter and fire light are its children.
- **Size:** every size-dependent value (box, light energy and radius, and the simulation correction tuned in Slice 5) is derived from the source's bounds at Create, so a cup and a house give the same-looking fire at their own scale.
- **Presets:** the Simulated Fire's three presets and Apply. On this kind a preset writes look and behaviour only: domain, flow, material and light values, scaled by the size correction. It keeps the fitted box and the emitter. Campfire is the default.
- **Everything else as the Simulated Fire:** Replay cache, cache folder rule, scoped `fluid_group` and `effector_group`, timeline following, light modes, wind, "(modified)" tracking, 0 planes.

## UI / UX Notes

- **Add panel:** "Fire and Smoke from Mesh" in the Fire group, after Burning Object. With no usable mesh selected, the panel's existing greyed note gives the reason in the same words as Burning Object's.
- **Redo panel:** the simulation preset choice, as the Simulated Fire shows it.
- **Create report:** "Press play from the first frame to see the fire, in Rendered or Solid view", plus the existing dense-mesh warning above 500,000 faces.
- **Effect box:** the Simulated Fire's notes and its full control list in both views, with **Burn From** straight after the preset row. Burn From is a dropdown: Whole Mesh, then each of the source's vertex groups. A note under it: painted weights set how strongly each part burns, so paint at 1 for full flames.
- **Error states, each a plain sentence in the box:** the chosen group is gone, naming it and saying to pick another in Burn From; the mesh is gone, saying to delete the fire and start again; the mesh is now over the face limit.

## Acceptance Criteria

- [x] **AC1 — Create.** With a mesh selected, the button builds an owned domain fitted around it, an emitter that reads it live and a fire light, all tagged for one effect, with a Replay cache. Playing from the first frame burns the whole mesh. It's preset number 9, shown after Burning Object, with the Campfire preset by default.
- [x] **AC2 — The buyer's mesh is never changed.** Its object, mesh data, modifiers, constraints, vertex groups and visibility are identical before and after Create, every control, Burn From, Apply and Delete.
- [x] **AC3 — Delete.** Delete removes only the effect's tagged IDs and its cache folder. The buyer's mesh stays, in its place.
- [x] **AC4 — Behaves as a Simulated Fire.** Its cache folder, timeline following, wind, "(modified)" tracking, light modes, Material Preview note and own-flows-only scope work as they do on the Simulated Fire.
- [x] **AC5 — Controls and presets.** Every Simulated Fire control is in its box in both views. Simulation settings show on the next play from the first frame; look settings show straight away. Apply sets a preset's look and behaviour and keeps the box fitted to the mesh.
- [x] **AC6 — Burn From.** Whole Mesh is the default. Choosing a group makes fire come only from it. Adding, removing or reordering the mesh's other groups doesn't change which part burns.
- [x] **AC7 — Weights.** A part painted at weight 0.5 burns measurably less than a part at 1, and weight 0 doesn't burn.
- [x] **AC8 — Breakage and refusals.** A renamed or deleted chosen group stops the fire and the box names it. Restoring it, or choosing another, brings the fire back on the next play from the first frame. A deleted mesh is reported in the box, and Delete still cleans up. Create refuses a non-mesh, an effect's own part, a mesh with no faces and one over 2,000,000 faces, in plain words, and warns above 500,000.
- [x] **AC9 — Size.** With the Campfire preset, cubes of 0.5, 2 and 8 m each burn with flames rising one to two times the cube's height above it, measured headless and judged in Cycles on 5.2. The values and the owner's verdict are recorded in `docs/LOOK_TEST.md`.
- [x] **AC10 — Moves.** A mesh moved or animated in place carries its fire: after the move, the flame centre is within a tenth of the mesh's width of the mesh's centre.
- [x] **AC11 — Speed.** A 2 m cube's first play-through runs at 5 fps or more in a windowed EEVEE viewport on 4.5.4 and 5.2.2, recorded in `docs/LOOK_TEST.md`.
- [x] **AC12 — Character.** A rigged mesh animated in place burns from one vertex group only, and the flames follow that part as it deforms.
- [x] **AC13 — Copies.** In a full scene copy, the copy's fire reads the copy's mesh, has its own cache folder and simulates on its own. Deleting it in either scene leaves the other working. A linked copy detaches, as other effects do.
- [x] **AC14 — Gate and docs.** 10 presets with numbers 0 to 8 unchanged. The release checklist has 40 eye checks and ten 4.5 renders, and the gate refuses a version with any open. README, troubleshooting, store page and glossary describe the preset.

## Technical Notes

**Paths** are relative to `Fire-and-Smoke/`.

**Where each piece lands:**

| Need | Where | Note |
| ---- | ----- | ---- |
| Kind, label, simulated kinds | `constants.py` `KIND_*`, `KIND_LABELS` | `tests/test_panel.py` requires every kind in `KIND_LABELS` to have controls |
| Preset | `effects/presets.py` `PRESETS`, `DISPLAY_ORDER`, `create()`, `FAS_OT_effect_create.draw` and `execute` | `draw` shows `sim_preset` only for `SIMULATED_CAMPFIRE`; `execute` reports per preset and already carries `@delete.guarded_create`; `create()` passes `context.active_object` for `BURNING_OBJECT` |
| Simulated build | `effects/sim_fire.py` `create_sim_fire`, `fill_box`, `clear_cache`, `domain_settings`, `flow_settings`, `set_look` | `flow_settings` reads the Fluid FLOW modifier on `entry.emitter`; the build order there (collection, domain, emitter, flow, domain settings, cache folder, light, `registry.add`, `light_mode.apply`, `sim_presets.apply`, `bounces.after_create`) is the one to follow |
| Mesh rules | `effects/mesh_fire.py` `source_problem`, `is_missing_source`, `MAX_FACES`, `WARN_FACES`, `_light_offset` | `_light_offset` puts a light above the mesh's top; its Copy Location with `use_offset` on the source is the following pattern |
| Live copy | `effects/plane_stack.py` builds `GeometryNodeObjectInfo` with `transform_space="RELATIVE"`; `effects/creation.py` sets the modifier input `Source` | Whether a full scene copy remaps that input to the copy's mesh is unmeasured: S024 checks it |
| Presets | `effects/sim_presets.py` `apply`, `_reshape`, `snapshot`, `note_edit`, `watch` | `_reshape` rebuilds the domain box and the emitter mesh from the package's `shape`; `apply` raises `NOT_SIMULATED` for any other kind |
| Entry settings | `core/registry.py` `FAS_EffectEntry`, `_simulation_change` | `source` is already a pointer on the entry; the simulation updates already go through `sim_fire.domain_settings` and `flow_settings`, which don't check the kind |
| Shared kind checks | `core/cache_folder.py` `simulated`; `effects/wind.py` `simulations_changed`; `core/covering.py` `FIRE_KINDS`, `_points`; `ui/panel.py` `entry_problem`, `_draw_entry`, `FAS_PT_main.draw` | Listed in Constraints |
| Handlers | `core/handlers.py` `fas_scene_watch` | Runs on `depsgraph_update_post`, the place for the vertex group mirror sync |
| Delete | `core/delete.py` `_sweep`, `_adopted`, `_DATA` | `_DATA` covers meshes, node groups, materials, lights and actions |
| Copies | `core/copies.py` `_split`, `_own_object`, `_own_tree` | `_own_tree` copies an owned Geometry Nodes tree and re-owns its materials |
| Panel | `ui/control_spec.py` `SIM_FIRE`, `SIMPLE`, `ADVANCED`; `ui/panel.py` `_draw_control`, `FAS_PT_create.draw` | `FAS_PT_create.draw` shows `mesh_fire.source_problem` as "Burning Object: …" |

**Fluid API**, the same on 4.5.4 and 5.2.2: `FluidFlowSettings.flow_source` (`MESH`), `surface_distance`, `density_vertex_group` (a name, set only from the emitter's own list); `FluidDomainSettings.time_scale`, `domain_resolution`, `flame_grid` (data only on the evaluated domain).

**Probe scripts** behind Constraints: a 2 × 1 m grid of 21 × 11 vertices at z = 0.1 with groups ["Other" at 0.3 everywhere, "Left" at 1 for x < 0], in a 2.6 × 1.6 × 2 m domain at 48 divisions, 24 frames; cubes on the ground in a box 2.2 *s* wide and 4 *s* tall at 64 divisions, 40 frames. Flame is summed from the evaluated domain's `flame_grid`, with x varying fastest.

**Tests:** `tests/test_<area>.py` files of `test_*` functions sharing a module `STATE`, ending in `lib.main(globals())`, run by `tests/run_tests.py` on every installed Blender. `tests/test_mesh_fire.py` has the source-untouched, follows-the-source, refusal, source-deleted and delete-leaves-the-source checks to mirror. `tests/test_sim_fire.py` has the create, burns, render, cache, own-flows, light, controls, timeline, delete and cache-folder checks. `tests/test_sim_look.py`, `tests/test_sim_presets.py` and `tests/test_wind.py` drive one Simulated Fire. `tests/render_presets.py` fails with a `KeyError` for a preset with no `SHOTS` entry, and builds a mesh for `BURNING_OBJECT`. `tests/gui_viewport_visible.py` builds its queue from `DISPLAY_ORDER`.

## Implementation Steps

| Phase | Meaning |
| ----- | ------- |
| F | Foundation |
| S | Service: simulation build, sync, handlers |
| U | UX |
| D | Docs |
| T | Tests and measurements |
| O | Owner action, done by hand |
| X | Cross-document work |

### Slice 1 — Burn the selected mesh

**Demoable when:** with the default cube selected, the new button builds the fire, playing from the first frame burns the whole cube, the cube is unchanged, and the bin icon removes everything the add-on made.
**Satisfies:** AC1, AC2, AC3

| Done | # | Phase | Title | Description | Depends on | Primary files |
| ---- | - | ----- | ----- | ----------- | ---------- | ------------- |
| ✅ | S001 | F | Add the kind and the preset | The `SIM_MESH_FIRE` kind, its label and the simulated-kinds group; `SIMULATED_MESH_FIRE` appended to `PRESETS` as number 9 and placed after `BURNING_OBJECT` in `DISPLAY_ORDER`; the Simulated Fire's control list for the kind in both `SIMPLE` and `ADVANCED`. | — | `constants.py`, `effects/presets.py`, `ui/control_spec.py` |
| ✅ | S002 | S | Build the fire on a mesh | Refuse with `mesh_fire.source_problem`. Build the domain around the source's world bounds with Copy Location (offset) on the source; the emitter as an empty mesh with the live-copy modifier and the Fluid flow, as in Architectural decisions; the light above the mesh's top. Emitter and light are the domain's children; every ID is tagged; the entry records the source, the emitter and 0 planes. Then apply the Campfire. | S001 | add-on package |
| ✅ | S003 | S | Treat it as a simulation everywhere | Every check listed in Constraints uses the simulated-kinds group: cache folder, wind, preset tracking, panel notes and problems, covering. Covering takes the domain and light as its points for this kind. | S001 | `core/cache_folder.py`, `effects/wind.py`, `effects/sim_presets.py`, `ui/panel.py`, `core/covering.py` |
| ✅ | S004 | S | Wire it to Create | Its branch in `create()` with the active object, the redo panel's simulation preset for it, the play report, and the Add panel's note when no usable mesh is selected. | S002 | `effects/presets.py`, `ui/panel.py` |
| ✅ | S005 | T | Test creation | New `tests/test_sim_mesh_fire.py`: creates on a cube; the cube's object, mesh, modifiers, constraints, groups and visibility are unchanged; the evaluated grids hold fire after frames 1 to 30 on both sides of the cube; a small Cycles render isn't dark; Delete leaves the cube and no tagged ID; a failed create leaves nothing. | S004 | `tests/test_sim_mesh_fire.py` |
| ✅ | S006 | T | Fix the preset counts | Extend: `tests/test_presets.py` expects 10 presets with `SIMULATED_MESH_FIRE` locked at 9; `tests/test_panel.py` expects 10 offered. | S001 | `tests/test_presets.py`, `tests/test_panel.py` |

### Slice 2 — Every Simulated Fire control on a mesh

**Demoable when:** each slider in the box changes the mesh's fire as it does the Simulated Fire's, and applying Candle Fire then Campfire changes the look while the box stays around the mesh.
**Satisfies:** AC4, AC5

| Done | # | Phase | Title | Description | Depends on | Primary files |
| ---- | - | ----- | ----- | ----------- | ---------- | ------------- |
| ✅ | S007 | S | Presets keep the fitted box | On this kind, `apply` writes the domain, flow, material and light values and skips the package's shape; the snapshot doesn't track the shape. | S002 | `effects/sim_presets.py` |
| ✅ | S008 | S | Check the sliders reach it | Detail, Flame Intensity, Flame Noise, Smoke Amount, the look sliders, light mode and Light Strength each reach this kind's domain, flow, material and light, and simulation changes clear its cache. | S002 | `core/registry.py`, `effects/sim_fire.py` |
| ✅ | S009 | T | Test controls and presets | Extend `tests/test_sim_mesh_fire.py`: each simulation slider clears the cache and a replayed frame differs; each look slider changes the material with the cache kept; Apply of each preset keeps the domain mesh and emitter, resets the sliders and clears "(modified)"; an edit sets it. Timeline changes move its range; Wind clears its cache; a flow of the buyer's inside its box changes nothing. | S007, S008, S003 | `tests/test_sim_mesh_fire.py` |

### Slice 3 — Burn From

**Demoable when:** painting a vertex group on the cube's top and choosing it in Burn From makes fire come only from the top, and Whole Mesh burns all of it again.
**Satisfies:** AC6, AC7

| Done | # | Phase | Title | Description | Depends on | Primary files |
| ---- | - | ----- | ----- | ----------- | ---------- | ------------- |
| ✅ | S010 | S | Store Burn From | A group name on the entry, empty for Whole Mesh, with a guarded update that sets the flow's vertex group and clears the cache. Saved fires load with Whole Mesh. | S002 | `core/registry.py` |
| ✅ | S011 | S | Mirror the vertex groups | Keep the emitter's list equal to the source's names in order: at Create, on a Burn From change, and from the depsgraph watch when the source's list differs. After a sync, the flow's vertex group is set again by name. | S010 | add-on package, `core/handlers.py` |
| ✅ | S012 | U | Show Burn From | A dropdown after the preset row listing Whole Mesh, then the source's groups, and the weights note. | S010 | `ui/control_spec.py`, `ui/panel.py` |
| ✅ | S013 | T | Test Burn From and weights | In `tests/test_sim_mesh_groups.py`, its own file, with the probe grid: "Left" burns the left half only (left at least 20 times right); adding a group before it, deleting another and reordering keep the left burning; Whole Mesh burns both; a half at weight 0.5 burns less than a half at 1, and weight 0 burns nothing; the buyer's groups are unchanged throughout. | S011, S012 | `tests/test_sim_mesh_groups.py` |

### Slice 4 — When something breaks

**Demoable when:** renaming the chosen group stops the fire with a sentence naming it, renaming it back brings it back after a replay, and deleting the cube leaves a box that says so and still deletes cleanly.
**Satisfies:** AC8

| Done | # | Phase | Title | Description | Depends on | Primary files |
| ---- | - | ----- | ----- | ----------- | ---------- | ------------- |
| ✅ | S014 | S | Stop on a missing group or mesh | Mute the flow's Fluid modifier in viewport and render while the chosen group isn't on the source or the source is gone, and unmute it when it's back, clearing the cache on each change. The missing-source check covers this kind. | S011 | add-on package, `effects/mesh_fire.py` |
| ✅ | S015 | U | Say what's wrong | The box's problem sentences for a missing group (naming it), a missing mesh and the face limit; the dense-mesh warning at Create. | S014 | `ui/panel.py`, `effects/presets.py` |
| ✅ | S016 | T | Test breakage and refusals | In `tests/test_sim_mesh_groups.py`: rename, delete and restore the chosen group; delete the source (sentence, Delete still clean); each refusal and the warning. Measure the headless cost per frame of a 500,000-face mesh and record it in `docs/LOOK_TEST.md`. | S015 | `tests/test_sim_mesh_groups.py`, `docs/LOOK_TEST.md` |

### Slice 5 — Size, movement and speed

**Demoable when:** a 0.5, 2 and 8 m cube each burn with flames one to two cube-heights tall, an animated cube carries its fire, and a 2 m cube plays at 5 fps or better in a window.
**Satisfies:** AC9, AC10, AC11

| Done | # | Phase | Title | Description | Depends on | Primary files |
| ---- | - | ----- | ----- | ----------- | ---------- | ------------- |
| ✅ | S017 | S | Derive values from the mesh's size | The box, the light's energy and radius, and a simulation correction derived from the source's bounds at Create, and reapplied by Apply. | S007 | add-on package, `effects/sim_presets.py` |
| ✅ | S018 | T | Tune the size correction by render | Probe flame height at 0.5, 2 and 8 m on 5.2 headless, then render each in Cycles (dark ground and sky, a few frames side by side); tune until each is one to two cube-heights; check 4.5 by render; record values and findings in `docs/LOOK_TEST.md`. | S017 | `docs/LOOK_TEST.md`, add-on package |
| ✅ | S019 | T | Test size and movement | In `tests/test_sim_mesh_size.py`: flame height at the three sizes is within the tuned range; a cube animated 1.5 m over 30 frames ends with its flame centre within a tenth of its width of the cube. | S018 | `tests/test_sim_mesh_size.py` |
| ✅ | S020 | T | Measure windowed speed | Make `tests/gui_viewport_speed.py` build the new preset on a 2 m cube, time the first play-through in an EEVEE viewport on 4.5.4 and 5.2.2, and record it in `docs/LOOK_TEST.md`. | S018 | `tests/gui_viewport_speed.py`, `docs/LOOK_TEST.md` |
| ✅ | S021 | O | Judge the sizes | The owner's Cycles verdict on the three sizes, recorded in `docs/LOOK_TEST.md`. | S018 | `docs/LOOK_TEST.md` |

### Slice 6 — A burning character

**Demoable when:** a rigged mesh waving an arm in place burns from the arm's vertex group only, and the flames move with the arm.
**Satisfies:** AC12

| Done | # | Phase | Title | Description | Depends on | Primary files |
| ---- | - | ----- | ----- | ----------- | ---------- | ------------- |
| ✅ | S022 | T | Test a rigged mesh | In `tests/test_sim_mesh_character.py`: build a two-bone armature and a skinned cylinder with "Lower" and "Upper" groups in the test, animate the upper bone swinging in place, burn from "Upper"; flame sits near the evaluated upper part at two frames with the arm in different places, and none near the lower part. | S013, S019 | `tests/test_sim_mesh_character.py` |
| ✅ | S023 | T | Render the character | A Cycles render of the test character at two frames for the owner, recorded in `docs/LOOK_TEST.md` with the verdict pending. | S022 | `docs/LOOK_TEST.md` |

### Slice 7 — Copies, gate and docs

**Demoable when:** a full scene copy burns its own copy of the mesh, `tests/run_tests.py --release` refuses while any new box is open, and the buyer docs describe the preset.
**Satisfies:** AC13, AC14

| Done | # | Phase | Title | Description | Depends on | Primary files |
| ---- | - | ----- | ----- | ----------- | ---------- | ------------- |
| ✅ | S024 | T | Test copied scenes | Extend `tests/test_copied_scene.py`: a full copy's emitter reads the copy's mesh, its domain follows the copy's mesh, it has its own cache folder, and deleting either leaves the other burning; a linked copy detaches. | S009 | `tests/test_copied_scene.py` |
| ✅ | S025 | S | Give a copy its own mesh | Make the copy's emitter, Copy Location and entry source point at the copy's mesh, in `_split`, wherever S024 finds the copy still on the original. | S024 | `core/copies.py` |
| ✅ | S026 | T | Make the preset scripts play it | A `SHOTS` entry and a mesh for `SIMULATED_MESH_FIRE` in `tests/render_presets.py`; `tests/gui_viewport_visible.py` selects a mesh and steps from frame 1 before capturing it. | S004 | `tests/render_presets.py`, `tests/gui_viewport_visible.py` |
| ✅ | S027 | T | Run the windowed undo check | A create, undo and redo sequence with the new preset in `tests/gui_undo.py`, run in a window on 4.5 and 5.2. | S014 | `tests/gui_undo.py` |
| ✅ | S028 | D | Extend the checklist | Eye checks for Fire and Smoke from Mesh in Cycles and EEVEE on 5.1 and 5.2, the EEVEE boxes judged on "renders visible fire", and a 4.5 render box. | S021 | `docs/RELEASE_CHECKLIST.md` |
| ✅ | S029 | T | Fix the gate counts | Extend `tests/test_release_gate.py`: 40 eye checks, ten 4.5 renders, and four "renders visible fire" boxes. | S028 | `tests/test_release_gate.py` |
| ✅ | S030 | D | Write the buyer docs | README Good to know: select a mesh first, the mesh stays visible, Burn From and painting at weight 1, the fire follows moves in place. TROUBLESHOOTING: the fire stopped (the group was renamed or deleted), weak fire (low weights), a character walking out of its fire's box, a rotated mesh leaving its box. STORE_PAGE: the feature and its limits. | S021 | `README.md`, `docs/TROUBLESHOOTING.md`, `docs/STORE_PAGE.md` |
| ✅ | S031 | D | Add the glossary terms | Fire and Smoke from Mesh, Burn From, Source mesh and Live copy in `reqs/GLOSSARY.md`. | S001 | `reqs/GLOSSARY.md` |
| ✅ | S032 | X | Update REQ-001's numbers | Change REQ-001's AC16 and AC19 to 10 presets and 40 eye checks, with a revision row. | S028 | `reqs/in-progress/REQ-001-Fire-And-Smoke-Addon.md` |

### Dependency graph

```
S001 → S002 → S004 → S005
S001 → S003
S001 → S006
S001 → S031
S002 → S007 → S017 → S018 → {S019, S020, S021}
S002 → S008
{S007, S008, S003} → S009 → S024 → S025
S002 → S010 → {S011, S012} → S013
S011 → S014 → S015 → S016
S014 → S027
{S013, S019} → S022 → S023
S004 → S026
S021 → S028 → {S029, S032}
S021 → S030
```

## Dependencies

| REQ ID | Title | Reason |
| ------ | ----- | ------ |
| REQ-001 | Fire and Smoke Add-on | Builds on its ownership, delete, copied scenes, handlers, panel, presets, Burning Object's mesh rules and release gate. Changes its AC16 and AC19 counts (S032). |
| REQ-002 | Simulated Campfire Preset | Reuses its domain, flow, Replay cache, cache folder rule, light and timeline following. |
| REQ-003 | Simulated Fire Presets | Reuses its presets, Apply and "(modified)" tracking, Flame Noise, the look sliders and Wind. Its open look verdicts (AC7, Q1, Q3) apply to this preset too. |

## Out of Scope

- A character or object that leaves its box through bone animation, rotation or a large move after Create: a Troubleshooting note only.
- Rotating or scaling the box with the mesh.
- Refitting the box after Create, or an adaptive domain.
- A smoke-only mode.
- New presets made for meshes.
- Volume emission from inside a closed mesh.
- Any change to Burning Object or the Simulated Fire, beyond the shared simulated-kinds checks.
- An end-to-end suite: windowed checks stay owner-run scripts.

## Open Questions

- [x] **Q1 — Resolved.** A new button and effect kind, beside Burning Object; the Simulated Fire and Burning Object stay as they are. *(Blaxine)*
- [x] **Q2 — Resolved.** The buyer's mesh is never changed: an owned emitter reads it live. *(Blaxine)*
- [x] **Q3 — Resolved.** The buyer's mesh stays visible and burns. *(Blaxine)*
- [x] **Q4 — Resolved.** Burn From is a dropdown starting on Whole Mesh, then the mesh's groups. *(Blaxine)*
- [x] **Q5 — Resolved.** Weights set how strongly each part burns. *(Blaxine)*
- [x] **Q6 — Resolved.** The box is fitted once and follows the mesh's moves. *(Blaxine)*
- [x] **Q7 — Resolved.** The three simulation presets set look and behaviour only; Campfire is the default. *(Blaxine)*
- [x] **Q8 — Resolved.** The fire scales with the mesh. *(Blaxine)*
- [x] **Q9 — Resolved.** A missing group or mesh stops the fire and the box says why. *(Blaxine)*
- [x] **Q10 — Resolved.** Always fire and smoke; no smoke-only mode. *(Blaxine)*
- [x] **Q11 — Resolved.** Done includes a rigged character animated in place. *(Blaxine)*
- [x] **Q12 — Resolved.** Seven slices, as below. *(Blaxine)*
- [x] **Q13 — Resolved, and approved by the owner in S021.** The time scale (size over 1.4 m, to the power 0.5), the burning rate (to the power -0.7, and 2.5 times faster on 4.5), and the material's density and glow (divided by the ratio). Heat buoyancy and the box's headroom stay. *(Tuned by render, `docs/LOOK_TEST.md`)*
- [ ] **Q14 — Blender 5.1.** Nothing has been measured on 5.1 on this PC. Deferred until 5.1 is installed here: rerun the probes behind Constraints and S005.

## Smoke Test

> Developer runs the app; the agent does not self-run.

1. Install the built zip in a clean profile and open the **Fire and Smoke** tab.
2. Select the default cube and click **Fire and Smoke from Mesh**. Switch to Rendered view and press play from the first frame. The cube burns all over and stays visible.
3. In Edit Mode, put the cube's top four vertices in a new vertex group at weight 1. Choose it in **Burn From**, go to the first frame and play. Only the top burns.
4. Rename the group. The fire stops and the box names the group. Rename it back, go to the first frame and play: it burns again.
5. Move the cube and play from the first frame: the fire moves with it.
6. Apply **Candle Fire**, then **Campfire**. The look changes and the box stays around the cube.
7. Delete the effect with the bin icon. Its objects and cache folder are gone, and the cube and its vertex group are exactly as they were.

## Size

| T-Shirt Size | Estimated Hours | Notes |
| ------------ | --------------- | ----- |
| L | 34 | About 12 hours of code across seven slices, 12 of tests and windowed checks, and 10 of size tuning, renders and owner eye checks |

## Considered And Rejected

Nothing here is built. Each entry names the alternative, then why it lost.

- **A Fluid modifier on the buyer's mesh, as Quick Smoke does.** It breaks the rule that the buyer's object is never changed, and an exported or applied mesh carries a modifier the buyer didn't add.
- **A one-time copy of the mesh.** Editing or moving the original afterwards leaves the fire behind.
- **A source switch on the Simulated Fire.** A fire could change source after it's made, which means rebuilding its domain, and the box gets more crowded.
- **Making Burning Object simulated.** Buyers lose the instant fire that scrubs with no simulation.
- **Hiding the buyer's mesh so only the fire shows.** It changes the buyer's object's visibility.
- **An emitter vertex group of its own with the chosen name.** The flow reads the group by position: probe B1 burned evenly and weakly (511.7 left, 510.4 right) against the control's 2724.8 and 3.7.
- **Storing the weights into an emitter-owned group with Geometry Nodes.** Store Named Attribute writes a plain attribute, so the flow still read position 0 of the buyer's list: the same 511.7 and 510.4.
- **A Blender enum of the mesh's groups for Burn From.** An enum stores a position, so a group added or removed before the chosen one silently changes which part burns.
- **Using a group automatically when the mesh has exactly one, or a group named "Fire".** The first surprises a buyer who forgot an old group; the second can't be discovered without the docs.
- **Burning any vertex in the group fully, whatever its weight.** A painted fade would do nothing, and the add-on would have to bake a 0 or 1 copy of the weights.
- **Burning the whole mesh when the chosen group is gone.** A buyer who chose only the roof could render a fully burning house without noticing.
- **Following a renamed group by its position.** A delete still needs the stop, and positions shift when other groups change.
- **A box that stays where it was made.** A cube moved 1.5 m ended with its flame centre at 0.87 m, cut off at the box's edge.
- **An adaptive domain.** It's slower and less predictable, and harder to make look right on both versions.
- **Scaling the box alone, or correcting with time scale.** Flame tops of 0.97, 0.48 and 0.39 of the box at 0.5, 2 and 8 m; time scale 0.5 at 8 m gave 0.34.
- **Real-world flame sizes.** A big mesh needs very high Detail to resolve small flames, which is slow, and a small one shows barely any fire.
- **A Flame Size slider.** One more control whose change needs a replay; the size correction is tuned once instead.
- **A Fire / Smoke / Both switch.** The flame sliders would do nothing in Smoke mode, and it adds a control and tests for a case nobody asked for.
- **Following a character that walks across the scene.** It needs a box that refits to the deformed mesh every frame or an adaptive domain.

## Revision History

| Date | Author | Summary of Change |
| ---- | ------ | ----------------- |
| 2026-11-05 | Blaxine | Initial plan. |
| 2026-11-05 | Blaxine | Moved to in-progress. Slice 1 built: the button burns the selected mesh all over, the mesh is unchanged, Delete is clean. S028, S029 and S032 done early, since the release gate checks every preset. |
| 2026-11-05 | Blaxine | Slice 2 built: every Simulated Fire control and preset works on a mesh fire, and Apply keeps the box fitted to the mesh. The own-flows check measures the box's corner: on 4.5 the fire's own smoke fills the cells beside the mesh, so a buyer's flow there showed no difference even unscoped. |
| 2026-11-06 | Blaxine | Slice 3 built: Burn From is stored by name with a menu that's a view of it (Whole Mesh, the groups, and a chosen group that's gone). The emitter mirrors the mesh's groups at Create, on a change and from the depsgraph watch, writing only what differs. Changing it isn't a preset edit, and Apply keeps it. Measured on both Blenders: Left burns 25 to 27 times more on the left; weight 0.5 burns at 40%; weight 0 burns nothing. The tests are in their own file, `tests/test_sim_mesh_groups.py`. |
| 2026-11-06 | Blaxine | Slice 4 built: a renamed or deleted chosen group, or a deleted mesh, mutes the flow in viewport and render and the box says why; it burns again when the group is back or another is chosen. Create warns above 500,000 faces; a 504,100-face grid costs 211 to 214 ms a frame headless. Found on 4.5: after a group is removed from Python, the copy kept its weights in the old order, so the sync now tags the mesh and the emitter to re-evaluate whenever the group list changes. |
| 2026-11-06 | Blaxine | S017 built: the mesh's largest size is measured once at Create, and Apply scales each preset to it. Time runs with the square root of the size, the burn slows with size (power 0.7, 2.5 times faster on 4.5, capped at Blender's 4.0), and the light's energy and radius follow the fire's area and size. The values are untuned until S018. `tests/gui_viewport_speed.py` can now build the new preset on a 2 m cube for S020. |
| 2026-11-06 | Blaxine | Slice 5 built, S018 to S020: tuned by render to a 1.4 m reference. The material's density and glow thin with size too: a big fire's smoke hid its flames and cube. 0.5, 2 and 8 m cubes burn 1.15 to 1.75 cube-heights above their top on both Blenders; a moving cube carries its fire; a 2 m cube plays at 10.7 fps (5.2) and 8.2 fps (4.5) in a window. Tests in `tests/test_sim_mesh_size.py`. S021, the owner's verdict, is open. |
| 2026-11-06 | Blaxine | S021: the owner judged the three sizes from the Cycles renders and said they look right. Q13 is settled. |
| 2026-11-06 | Blaxine | Slice 6 built: a 2 m cylinder skinned to a two-bone armature, its arm swinging 60 degrees each way, burns from "Upper" only and the flames follow the arm: 39 to 91% of the flame by the arm where it is, 11 to 29% by where it was or will be, 1 to 3% by the lower part, on both Blenders. Nothing in the add-on needed changing. Rendered at frames 24 and 48; the owner's verdict is pending. Tests in `tests/test_sim_mesh_character.py`. |
| 2026-11-06 | Blaxine | S023: the owner judged the character render and said it looks right. |
| 2026-11-06 | Blaxine | Slice 7 built. Copied scenes already worked: Blender points a full copy's emitter, Copy Location and entry at the copy's mesh, so S025 needed no code. `tests/test_copied_scene.py` covers it, with a linked copy that detaches. The preset render script, the viewport visibility script and the windowed undo check play the new preset, and both windowed scripts now leave saved preferences alone. Troubleshooting, store page and glossary finished. Every criterion ticked for 4.5 and 5.2; 5.1 and the release eye checks stay open. |
