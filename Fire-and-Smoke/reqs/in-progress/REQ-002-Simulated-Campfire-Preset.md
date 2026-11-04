# REQ-002 — Simulated Campfire Preset

| Field | Value |
| ----- | ----- |
| ID | REQ-002 |
| Title | Simulated Campfire Preset |
| SOLVE | — |
| Status | InProgress |
| Phase | New preset, pre-1.0 |
| Tier | Feature |
| Area | One new effect kind: Mantaflow emitter and domain, cache folder lifecycle, fire light, panel controls, presets, release gate |
| Author | Blaxine |
| Created | 2026-11-03 |
| Last Updated | 2026-11-04 |

> Grilled in conversation on 2026-11-03, with no PRD. It builds on REQ-001 and changes two of its numbers: 9 presets instead of 8, and 36 eye checks instead of 32. See Dependencies.

## Short Description

A ninth preset, **Simulated Campfire**, for the same beginners as the rest of the add-on. It builds the kind of fire and smoke that Blender's Quick Smoke makes, a real Mantaflow simulation with volumetric flames, and keeps every add-on rule: it's owned, tagged, scoped to its own effect, deleted cleanly and safe in copied scenes. It uses Mantaflow's Replay cache, so there's no bake step. Like embers, it simulates as you play from the first frame. It's held to the look bar in Cycles. In EEVEE it only has to render. The plane-based Campfire stays as it is.

## Constraints

Measured on Blender 4.5.4 and 5.2.2 on this PC on 2026-11-03, with a 0.35 m disc emitter in a 1.4 × 1.4 × 2.6 m domain, headless. 5.1 isn't installed on this PC, so nothing here is measured on it.

- **Replay only simulates forward from the last simulated frame.** Jumping past it, or skipping a single frame (41 → 43), holds the last simulated state and adds nothing. Going back to frame 1 and playing recovers. Scrubbing back within simulated frames reads the cache in 2 to 8 ms.
- **A Python change to flow settings doesn't clear the Replay cache.** Frames replayed after setting `fuel_amount` showed the old values. Reassigning a domain cache property to its own value (`cache_frame_end`) clears it, and so does `fluid.free_all`.
- **A domain with no `fluid_group` takes every flow in the scene.** A second emitter inside a domain gave a density sum of 580, against 295 with `fluid_group` set to the domain's own collection. `effector_group` works the same way. The buyer's own unscoped domain will also take this effect's emitter, and the flow side has no setting to prevent it.
- **A full scene copy shares the cache folder.** It remaps `fluid_group` and `effector_group` to the copied collection and shares the material, but both domains keep the same `cache_directory`, on 4.5 and 5.2.
- **`//` paths in an unsaved file resolve against Blender's working directory.** `bpy.path.abspath("//fas_cache/abc")` returned `fas_cache/abc`. `bpy.app.tempdir` is a per-session folder, and a new domain's default cache path sits inside it.
- **Cost per frame by resolution, frames 49 to 96:** 32 divisions ≈ 14 ms, 48 ≈ 40 ms, 64 ≈ 57 ms, 96 ≈ 210 ms, the same on both versions. The cache grows by about 0.12, 0.30, 0.56 and 1.4 MB per frame. A 250-frame timeline at 64 divisions writes about 140 MB.
- **Blender's Quick Smoke never turns noise on.** `if self.style == {'FIRE', 'BOTH'}` compares a string with a set, on 4.5 and 5.2. Its flow objects get `display_type = 'WIRE'` but still render. 4.5 adds modifiers through `object.modifier_add` with a context override; `Object.modifiers.new` worked on both versions in every probe.
- **Delete keeps any owned object that isn't parented to the primary.** `delete._adopted` treats it as the buyer's.
- **One 4.5.4 probe crashed with `EXCEPTION_ACCESS_VIOLATION`.** It read grids from the original (non-evaluated) domain. Every rerun that read `density_grid` and `flame_grid` from the evaluated object passed. Replays matched between 4.5 and 5.2 to within 0.5%, but on 4.5 a replay after `fluid.free_all` differed by 6%.
- **Light Strength 0 and back removes the flicker for good, on every fire today.** `fire_light.set_energy` scales the Noise modifier by `energy / old`, so on 5.2 the strength went from 27 to 0 and stayed there.

## Architectural decisions

- **Identity:** a new effect kind `SIM_FIRE`, labelled "Simulated Fire". A new preset `SIMULATED_CAMPFIRE`, fixed number 8, labelled "Simulated Campfire", in the Fire group, displayed straight after Campfire.
- **Ownership:** the domain is the effect's primary. Its mesh is built at full size with an object scale of 1. The emitter and the fire light are its children. Every ID carries the effect's `fas_owner` tag and sits in the effect's collection.
- **Build:** the add-on creates the emitter, domain, Fluid modifiers and volume material itself and never calls `object.quick_smoke`. The starting values follow Quick Smoke: flow type Smoke & Fire, Inflow, surface distance 1.0; domain CFL 4.0, OpenVDB cache format; Principled Volume with density 5 and blackbody intensity 1. The emitter is hidden from renders.
- **Scope:** the domain's `fluid_group` and `effector_group` are both the effect's own collection.
- **Cache:** Replay cache type. The cache folder is `<bpy.app.tempdir>/fas_cache/<uuid>` while the .blend is unsaved, and `//fas_cache/<uuid>` once it's saved. It's re-pointed after every save. A copy split off by `copies.reidentify` gets the path for its new uuid.
- **Cache deletion:** Delete removes an effect's cache folder only when the folder's name is that effect's uuid, its parent is named `fas_cache`, and it resolves inside the .blend's folder or `bpy.app.tempdir`. Anything else stays on disk.
- **Clearing the cache:** every change the add-on makes to a simulation setting clears the cache by reassigning a domain cache property.
- **Detail:** domain resolution, 64 divisions by default.
- **Light:** the existing owned fire light and Real, Emissive and Both light modes, with Real as the default. The mode acts on the domain object's ray visibility.
- **Timeline:** the domain's cache range follows the scene's frame range under the embers rule. A range the buyer set stays theirs.
- **Engines:** the owner's look bar applies in Cycles. In EEVEE the effect has to render visible fire without errors.
- **Bounce limit:** the effect records 0 planes and doesn't change transparent bounces.

## UI / UX Notes

- **Add panel:** "Simulated Campfire" in the Fire group, straight after "Campfire".
- **Create report:** "Press play from the first frame to see the fire", alongside the existing no-camera warning.
- **Effect box notes, in plain words:** it simulates as you play, so press play from the first frame, and if the fire looks frozen, go back to the first frame and play again. EEVEE shows a weaker look than Cycles. Higher Detail is slower and uses more disk space.
- **Simple controls:** Detail, Flame Intensity, Smoke Amount, Light, Light Strength. Advanced shows the same list.
- **Error states, each with a plain message and no traceback:** the effect's object is gone; Blender was built without Fluid (`bpy.app.build_options.fluid` is false).

## Acceptance Criteria

- [ ] **AC1 — Create.** Simulated Campfire creates an owned emitter, domain and volume material at the 3D cursor, all tagged for one effect, with a Replay cache at 64 divisions. Nothing the buyer had selected changes. It's preset number 8, shown after Campfire.
- [ ] **AC2 — Engines.** The owner passes it by eye in Cycles on 5.1 and 5.2. It renders visible fire without errors in EEVEE on 4.5, 5.1 and 5.2. The panel and store page say EEVEE shows a weaker look.
- [ ] **AC3 — Speed.** The default's first play-through runs at 5 fps or more in an EEVEE viewport, in a window, on this PC, recorded in `docs/LOOK_TEST.md` for each version.
- [ ] **AC4 — Isolation.** The domain takes flows and effectors only from its own collection. A second Simulated Campfire, or a flow of the buyer's placed inside its domain, changes nothing in it.
- [ ] **AC5 — Controls.** Detail, Flame Intensity, Smoke Amount, Light and Light Strength appear in Simple view. Each change shows on the next play from the first frame. Detail says it gets slower.
- [ ] **AC6 — Light.** Real, Emissive and Both, with Real as the default. Real flickers with no Python running. In Emissive the light is off and the flames light the scene in Cycles.
- [ ] **AC7 — Flicker survives zero.** For every fire effect, setting Light Strength to 0 and back restores the original flicker.
- [ ] **AC8 — Cache folder.** Each effect has its own folder: in the session temp folder while the file is unsaved, and in `fas_cache/<uuid>` beside the .blend after saving. An effect in a copied scene gets its own folder. Delete removes the folder only when it passes the path check, and never removes anything else.
- [ ] **AC9 — Delete and copies.** Delete removes only the effect's tagged IDs and its cache folder. Effects in a full copy simulate independently, and deleting one in either scene leaves the other working.
- [ ] **AC10 — Timeline.** The simulation range follows timeline changes, unless the buyer set their own range on the domain.
- [ ] **AC11 — Presets and gate.** 9 presets, with numbers 0 to 7 unchanged. The release checklist has 36 eye checks and nine 4.5 renders, and the gate refuses a version with any of them open.
- [ ] **AC12 — Docs.** README, troubleshooting and store text state that the preset replays from the start, the Cycles-first look, its disk use and where the folder lives, and how to recover a frozen fire.

## Technical Notes

**Paths** are relative to `Fire-and-Smoke/`. New files are named only where the plan fixes them.

**Where each piece lands:**

| Need | Where | Note |
| ---- | ----- | ---- |
| Kind and label | `constants.py` `KIND_*`, `KIND_LABELS` | `test_panel.py:60` requires every kind in `KIND_LABELS` to have controls |
| Preset | `effects/presets.py` `PRESETS`, `DISPLAY_ORDER`, `create()` | Append to `PRESETS`; `FAS_OT_effect_create.execute` already reports a raised bounce limit and a missing camera |
| Non-plane create shape | `effects/embers.py` `create_embers` | `naming.new_effect_collection`, `naming.tag`, `registry.add`, base fields on the entry, then `bounces.after_create` |
| Create rollback | `core/delete.py` `guarded_create` | Sweeps every uuid that appeared during a failed create |
| Entry settings | `core/registry.py` `FAS_EffectEntry` | Settings scale `base_*` fields; updates use `errors.guard_update`. New properties with defaults load in old files, so `DATA_VERSION` stays 1 |
| Delete | `core/delete.py` `_sweep`, `_DATA`, `_adopted` | `_DATA` already covers meshes, materials, lights and actions; no file handling today |
| Copied scenes | `core/copies.py` `_split`, `_own_object` | `_own_object` re-owns Geometry Nodes trees, materials and particle settings; it doesn't touch Fluid modifiers |
| Timeline and save hooks | `core/handlers.py` `_follow_range`, `register` | `_follow_range` handles only `KIND_EMBERS`; there's no `save_post` handler yet; `bpy.app.handlers.save_post` exists on 4.5 and 5.2 |
| Fire light | `effects/fire_light.py` `build_light`, `set_energy`, `get_energy` | Noise strength is set from `energy * flicker` at build |
| Light modes | `effects/light_mode.py` `apply` | Sets `visible_shadow = False` on the primary in every mode, so the domain's smoke casts no shadows |
| Panel | `ui/control_spec.py` `SIMPLE`, `ADVANCED`; `ui/panel.py` `_draw_entry` | Notes per kind branch on `entry.kind`, as `EMBERS_NOTE` does |

**Fluid API**, the same on 4.5.4 and 5.2.2:

- `FluidDomainSettings`: `cache_type` (`REPLAY`, `MODULAR`, `ALL`; default `REPLAY`), `cache_directory`, `cache_frame_start` and `cache_frame_end` (default 1 and 250), `resolution_max` (default 32), `use_noise`, `cache_data_format`, `fluid_group`, `effector_group`, `cfl_condition`, `burning_rate` 0.75, `flame_smoke` 1.0, `flame_ignition` 1.5, `flame_max_temp` 3.0.
- `FluidFlowSettings`: `flow_type`, `flow_behavior`, `surface_distance`, `fuel_amount` 1.0, `temperature` 1.0, `density` 1.0, `smoke_color`, `subframes` 0.
- Grids: `density_grid` and `flame_grid` hold data only on the evaluated domain (`obj.evaluated_get(depsgraph)`).

**Probe setup used for every measurement:** an emitter disc of radius 0.35 m at z = 0.05, and a domain of 1.4 × 1.4 × 2.6 m centred at z = 1.25. These are the starting values for tuning, not final ones.

**Tests:** `tests/test_<area>.py` files with `test_*` functions, ending in `lib.main(globals())`, run by `python tests/run_tests.py`. Helpers in `tests/fas_testlib.py`: `render`, `eevee_id`, `darkest`, `mean_diff`, `clear_scene`. Every test that plays the simulation steps `frame_set` one frame at a time from frame 1, and compares grids with a tolerance.

**Scripts that loop over every preset:** `tests/render_presets.py` looks up `SHOTS[preset_id]` and fails with a `KeyError` for a preset that has no entry. `tests/gui_viewport_visible.py` builds its queue from `DISPLAY_ORDER`.

## Implementation Steps

| Phase | Meaning |
| ----- | ------- |
| F | Foundation |
| S | Service: simulation build, cache, handlers, light |
| U | UX |
| D | Docs |
| T | Tests |
| O | Owner action, done by hand |
| X | Release and cross-document work |

### Slice 1 — Create and render

**Demoable when:** the panel's Simulated Campfire button builds the effect, playing from frame 1 fills the domain with fire, a small Cycles render shows it, and the bin icon removes every tagged ID.
**Satisfies:** AC1, AC4

| Done | # | Phase | Title | Description | Depends on | Primary files |
| ---- | - | ----- | ----- | ----------- | ---------- | ------------- |
|  | S001 | O | Confirm the look gate | REQ-001's AC1 has a recorded pass in `docs/LOOK_TEST.md`. No other step starts without it. | — | `docs/LOOK_TEST.md` |
| ✅ | S002 | F | Add the kind and the preset | The `SIM_FIRE` kind and its label; `SIMULATED_CAMPFIRE` appended to `PRESETS` as number 8 and placed after Campfire in `DISPLAY_ORDER`; an empty controls entry for the kind. | S001 | `constants.py`, `effects/presets.py`, `ui/control_spec.py` |
| ✅ | S003 | S | Build the simulation | Owned emitter and domain as in Architectural decisions: domain as primary at full size, emitter as its child and hidden from renders, Replay at 64 divisions, both groups set to the effect's collection, cache range taken from the timeline, a cache folder in the session temp folder under the uuid, and the Principled Volume material. Every ID is tagged. Record the entry with 0 planes. Refuse with a plain message when Blender has no Fluid. | S002 | add-on package |
| ✅ | S004 | S | Wire it to the preset | The preset's branch in `create()`, the create report and the rollback guard. | S003 | `effects/presets.py` |
| ✅ | S005 | U | Show the effect's box | The box title and the replay note for the kind. | S004 | `ui/panel.py` |
| ✅ | S006 | T | Test creation | New `tests/test_sim_fire.py`: creates; the buyer's selected object is unchanged; evaluated grids hold fire after frames 1 to 30; a second Simulated Campfire's emitter inside the domain and a buyer's flow inside it change nothing; a small Cycles render isn't dark; Delete leaves no tagged ID. | S004 | `tests/test_sim_fire.py` |
| ✅ | S007 | T | Fix the preset counts | Extend: `tests/test_presets.py` expects 9 presets with `SIMULATED_CAMPFIRE` locked at 8; `tests/test_panel.py` expects 9 offered. | S002 | `tests/test_presets.py`, `tests/test_panel.py` |

### Slice 2 — Cache folder lifecycle

**Demoable when:** saving the file puts the cache beside it in `fas_cache/<uuid>`, a full scene copy plays with its own folder, and deleting an effect removes its folder and nothing else.
**Satisfies:** AC8, AC9

| Done | # | Phase | Title | Description | Depends on | Primary files |
| ---- | - | ----- | ----- | ----------- | ---------- | ------------- |
| ✅ | S008 | S | Apply the path rule at create | Session temp folder while unsaved, `//fas_cache/<uuid>` when saved. | S003 | add-on package |
| ✅ | S009 | S | Re-point after saving | A persistent `save_post` handler, registered and unregistered with the others, gives every Simulated Campfire domain in every scene the path the rule now gives. The folder at the old path stays. | S008 | `core/handlers.py` |
| ✅ | S010 | S | Remove the folder on Delete | After the ID sweep, remove the effect's cache folder when it passes the path check in Architectural decisions; otherwise leave it. Failed creates go through the same path. | S008 | `core/delete.py` |
| ✅ | S011 | S | Split the cache in copies | A domain re-owned by `_split` gets the path for its new uuid. Linked copies don't change. | S008 | `core/copies.py` |
| ✅ | S012 | T | Test the folder | Extend `tests/test_sim_fire.py`: an unsaved path lies under `bpy.app.tempdir`; saving re-points it; Delete removes the folder; a folder with another name, or outside both roots, is never removed. Extend `tests/test_copied_scene.py`: the copy gets its own folder, and deleting it leaves the original's. Extend `tests/test_create_delete.py`: a failed create leaves no folder. | S009, S010, S011 | listed files |

### Slice 3 — Light and the flicker fix

**Demoable when:** the Simulated Campfire lights the ground with a flickering light, Emissive lets the flames light it in Cycles, and Light Strength 0 and back keeps the flicker on every fire.
**Satisfies:** AC6, AC7

| Done | # | Phase | Title | Description | Depends on | Primary files |
| ---- | - | ----- | ----- | ----------- | ---------- | ------------- |
| ✅ | S013 | S | Keep the flicker through zero | `set_energy` sets the noise strength from the light's own flicker ratio, so any energy, including 0, gives back the built flicker. It covers every fire kind. | — | `effects/fire_light.py` |
| ✅ | S014 | T | Test the flicker fix | Extend `tests/test_light.py`: Light Strength 0, then 1, restores the original noise strength. It fails before S013. | S013 | `tests/test_light.py` |
| ✅ | S015 | S | Light the Simulated Campfire | The owned fire light as a child of the domain at flame height, with its light, data and action tagged; `light_mode.apply` on the domain; `base_energy` on the entry. | S003, S013 | add-on package |
| ✅ | S016 | T | Test the light | Extend `tests/test_sim_fire.py`: Real hides the domain from diffuse and glossy rays; Emissive turns the light off; in Cycles, Emissive lights the ground where Real with the light off doesn't; the light's energy changes over frames. | S015 | `tests/test_sim_fire.py` |

### Slice 4 — Controls and timeline

**Demoable when:** each slider in the box changes the fire on the next play from frame 1, and lengthening the timeline lengthens the simulation.
**Satisfies:** AC5, AC10

| Done | # | Phase | Title | Description | Depends on | Primary files |
| ---- | - | ----- | ----- | ----------- | ---------- | ------------- |
|  | S017 | S | Add the settings | Entry properties for Detail (resolution), Flame Intensity (scales the flow's fuel) and Smoke Amount (scales the flow's smoke and the material's density), each with a guarded update that clears the cache. | S003 | `core/registry.py` |
|  | S018 | U | Show the controls | Simple and Advanced lists for the kind: Detail, Flame Intensity, Smoke Amount, Light, Light Strength. The Detail note. | S017, S015 | `ui/control_spec.py`, `ui/panel.py` |
|  | S019 | S | Follow the timeline | Extend `_follow_range` to Simulated Campfire domains: the cache range moves with the timeline while it still equals the old range. | S003 | `core/handlers.py` |
|  | S020 | T | Test controls and timeline | Extend `tests/test_sim_fire.py`: each slider reaches its setting and a replayed frame differs; timeline changes move the range; a range the buyer set stays. Extend `tests/test_panel.py`: the kind's controls draw on the stand-in layout. | S017, S018, S019 | `tests/test_sim_fire.py`, `tests/test_panel.py` |

### Slice 5 — Engines, speed and look

**Demoable when:** `docs/LOOK_TEST.md` holds the Simulated Campfire's windowed speed on every installed version and the owner's Cycles verdict, and EEVEE renders it on every version.
**Satisfies:** AC2, AC3

| Done | # | Phase | Title | Description | Depends on | Primary files |
| ---- | - | ----- | ----- | ----------- | ---------- | ------------- |
|  | S021 | T | Test EEVEE | Extend `tests/test_sim_fire.py`: after frames 1 to 30, an EEVEE render isn't dark and reports no error. The engine id comes from `lib.eevee_id()`. | S006 | `tests/test_sim_fire.py` |
|  | S022 | T | Measure windowed speed | Extend `tests/gui_viewport_speed.py` to time the default's first play-through in an EEVEE viewport. Record the results for 4.5, 5.1 and 5.2 in `docs/LOOK_TEST.md`. | S018 | `tests/gui_viewport_speed.py`, `docs/LOOK_TEST.md` |
|  | S023 | T | Make the preset scripts play it | Add a `SHOTS` entry for `SIMULATED_CAMPFIRE` in `tests/render_presets.py`, and have it and `tests/gui_viewport_visible.py` step from frame 1 before capturing this preset. | S004 | `tests/render_presets.py`, `tests/gui_viewport_visible.py` |
|  | S024 | O | Tune and judge in Cycles | Render it, tune the emitter, domain and material values until it looks right, and record the verdict and final values in `docs/LOOK_TEST.md`. | S020, S023 | `docs/LOOK_TEST.md`, add-on package |
|  | S025 | T | Run the windowed undo check | Run `tests/gui_undo.py` sequences with the new preset in a window on 4.5, 5.1 and 5.2, and add a sequence if create, undo and redo isn't covered. | S012 | `tests/gui_undo.py` |

### Slice 6 — Gate and docs

**Demoable when:** `python tests/run_tests.py --release` refuses while any of the new boxes is open, and the buyer docs describe the preset.
**Satisfies:** AC11, AC12

| Done | # | Phase | Title | Description | Depends on | Primary files |
| ---- | - | ----- | ----- | ----------- | ---------- | ------------- |
|  | S026 | D | Extend the checklist | Eye checks for Simulated Campfire in Cycles and EEVEE on 5.1 and 5.2, with the EEVEE boxes judged on "renders visible fire", plus a 4.5 render box. | S024 | `docs/RELEASE_CHECKLIST.md` |
|  | S027 | T | Fix the gate counts | Extend `tests/test_release_gate.py`: 36 eye checks and nine 4.5 renders. | S026 | `tests/test_release_gate.py` |
|  | S028 | D | Write the buyer docs | README Good to know: plays from the first frame, Cycles-first look, cache size and location, removal on delete, and that the buyer's own domains without a Flow collection also take its emitter. TROUBLESHOOTING: frozen fire. STORE_PAGE: the same limits. | S024 | `README.md`, `docs/TROUBLESHOOTING.md`, `docs/STORE_PAGE.md` |
|  | S029 | D | Add the glossary terms | Simulated Campfire, Domain, Flow, Replay cache, Cache folder and Detail in `reqs/GLOSSARY.md`. | S002 | `reqs/GLOSSARY.md` |
|  | S030 | X | Update REQ-001's numbers | Change REQ-001's AC16 and AC19 to 9 presets and 36 eye checks, with a revision row. | S026 | `reqs/in-progress/REQ-001-Fire-And-Smoke-Addon.md` |

### Dependency graph

```
S001 → S002 → S003 → S004 → S005
S002 → S007
S002 → S029
S004 → S006 → S021
S004 → S023
S003 → S008 → {S009, S010, S011} → S012 → S025
S013 → S014
{S003, S013} → S015
S003 → S017
{S017, S015} → S018 → S022
S003 → S019
{S017, S018, S019} → S020
{S020, S023} → S024 → S026 → S027
S026 → S030
S024 → S028
```

## Dependencies

| REQ ID | Title | Reason |
| ------ | ----- | ------ |
| REQ-001 | Fire and Smoke Add-on | Needs its recorded look-test pass (AC1) before starting, and builds on its effect records, delete, copied scenes, handlers, fire light, panel, presets and release gate. Changes its AC16 and AC19 counts (S030). |

## Out of Scope

- A bake button, or the Modular and All cache types.
- Mantaflow's noise pass.
- Moving a cache folder when Save As changes the file's folder: the old folder stays where it was.
- Cleaning up `fas_cache` folders left by effects deleted in other sessions or outside the add-on.
- Any change to the plane-based Campfire or the other 7 presets, other than the flicker fix.
- Stopping the buyer's own unscoped domains from taking the emitter: a docs note only.
- Advanced-only controls and a Variation seed.
- An end-to-end suite: windowed checks stay owner-run scripts.

## Open Questions

- [x] **Q1 — Resolved.** It's a real Mantaflow simulation. *(Blaxine)*
- [x] **Q2 — Resolved.** A new ninth preset; the plane Campfire stays. *(Blaxine)*
- [x] **Q3 — Resolved.** Replay cache, with no bake step. *(Blaxine)*
- [x] **Q4 — Resolved.** Cycles is held to the look bar; EEVEE has to render. *(Blaxine)*
- [x] **Q5 — Resolved.** The add-on builds the setup itself and never calls Quick Smoke. *(Blaxine)*
- [x] **Q6 — Resolved.** A measured speed cap of at least 5 fps on the first pass, with a Detail slider; 64 divisions by default. *(Blaxine)*
- [x] **Q7 — Resolved.** It reuses Real, Emissive and Both. *(Blaxine)*
- [x] **Q8 — Resolved.** A uuid-named cache folder: session temp until saved, then beside the .blend; Delete removes it after the path check. *(Blaxine)*
- [x] **Q9 — Resolved.** REQ-001's look-test kill rule still decides the project; this preset starts only after a pass. *(Blaxine)*
- [x] **Q10 — Resolved.** Simple controls: Detail, Flame Intensity, Smoke Amount, Light, Light Strength. *(Blaxine)*
- [x] **Q11 — Resolved.** The simulation range follows the timeline under the embers rule. *(Blaxine)*
- [x] **Q12 — Resolved.** Flows and effectors come only from the effect's own collection. *(Blaxine)*
- [x] **Q13 — Resolved.** The flicker fix is a step in this plan. *(Blaxine)*
- [ ] **Q14 — Single-frame renders past the cache.** What does F12 on a frame past the simulated range show, and should the add-on warn before it renders? Deferred until S021's render check shows what it renders.
- [ ] **Q15 — Detail range.** The slider's soft maximum. Deferred until S022's windowed measurement.
- [ ] **Q16 — Final emitter and domain values.** Deferred until the owner's Cycles verdict in S024.
- [ ] **Q17 — Blender 5.1.** Nothing has been measured on 5.1 on this PC. Deferred until 5.1 is installed here: rerun the probes behind Constraints and S006.

## Smoke Test

> Developer runs the app; the agent does not self-run.

1. Install the built zip in a clean profile and open the **Fire and Smoke** tab.
2. Click **Simulated Campfire**, switch to Material Preview, and press play from the first frame. Fire and smoke rise inside the domain.
3. Scrub back: the simulated frames show straight away. Jump far ahead: the fire holds. Go back to the first frame and play: it continues.
4. Change Detail, go to the first frame and play: the fire is finer and plays slower.
5. Save the file. A `fas_cache/<uuid>` folder appears beside it after the next play.
6. Make a full copy of the scene and play both: each has its own folder.
7. Switch Light to Emissive and render one Cycles frame after playing to it. Then try EEVEE.
8. Delete the effect with the bin icon. Its objects and its cache folder are gone, and nothing else changed.

## Size

| T-Shirt Size | Estimated Hours | Notes |
| ------------ | --------------- | ----- |
| L | 30 | About 12 hours of code across six slices, 10 of tests and windowed checks, and 8 of owner tuning and eye checks on three versions |

## Considered And Rejected

Nothing here is built. Each entry names the alternative, then why it lost.

- **Calling `object.quick_smoke`.** It adds a Fluid modifier to the buyer's selected objects, creates an untagged "Smoke Domain", differs between 4.5 and 5.2, and its noise branch never runs.
- **Burning the buyer's selected mesh, as Quick Smoke does.** It breaks the rule that the buyer's object is never changed.
- **Plane fire with simulated smoke.** It still needs a cache, and two systems would have to stay in step.
- **Replacing the plane Campfire.** It voids the measured speed results (2.63x Cycles, 59.9 fps EEVEE) and the pending look verdict.
- **Swapping out a weaker preset.** Preset numbers can't be reused, so the list grows anyway.
- **A Simulate switch on every fire.** It doubles every fire's testing and adds a mode beginners would get wrong.
- **The simulated campfire as the look-test fallback.** The product's headline, "no baking", wouldn't survive a plane fail.
- **A bake button.** It needs a saved file first, takes minutes, and needs a rebake after every slider change.
- **Baking on create.** Blender freezes on the first click, which beginners read as a crash.
- **Blender's own Physics panel for baking.** It puts Mantaflow's full settings in front of the beginners the panel exists to shield from them.
- **Holding EEVEE to the Cycles look.** It needs EEVEE volume settings changed on create, and could fail the gate outright.
- **Cycles only.** It's the first preset that wouldn't work in a supported engine.
- **96 divisions by default.** 210 ms per frame headless, about 4.7 fps before any drawing, and about 360 MB per 250 frames.
- **48 divisions by default.** Coarse enough to look blocky in EEVEE.
- **No `fluid_group` on the domain.** A neighbouring emitter doubled its density (580 against 295).
- **All scene effectors.** The look would depend on the buyer's scene, and the eye checks wouldn't hold.
- **Blender's default cache path.** Full copies share it on 4.5 and 5.2, and the add-on wouldn't know where its files are.
- **Always caching in the temp folder.** The cache is lost on every restart.
- **Refusing to create until the file is saved.** It would be the only preset with a precondition on the first click.
- **Never deleting cache files.** About 140 MB per effect per 250 frames would pile up beside the buyer's files.
- **Setting the range once, or a fixed 1 to 250.** That repeats AquaSuite's emitters stopping at the old timeline end.
- **Relying on a setting change to clear the cache.** Frames replayed after a Python change to `fuel_amount` showed the old values.
- **Fixing the flicker outside a plan, or as a REQ-001 step.** The first is unreviewed shared-code work; the second makes this plan wait on unfinished REQ-001 work.

## Revision History

| Date | Author | Summary of Change |
| ---- | ------ | ----------------- |
| 2026-11-03 | Blaxine | Initial plan. |
| 2026-11-04 | Blaxine | Moved to in-progress. |
