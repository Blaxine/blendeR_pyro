# REQ-003 — Simulated Fire Presets

| Field | Value |
| ----- | ----- |
| ID | REQ-003 |
| Title | Simulated Fire Presets |
| SOLVE | — |
| Status | InProgress |
| Phase | Feature on REQ-002's preset, pre-1.0 |
| Tier | Feature |
| Area | Simulated Fire: preset catalogue, Create, effect box, registry, handlers, docs |
| Author | Blaxine |
| Created | 2026-11-04 |
| Last Updated | 2026-11-04 |

> Asked for in conversation on 2026-11-04, with no PRD and no grilling: "look at aqua and look how it does the water simulation presets, i want to do exactly the same here with fire simulation, a preset of normal fire, candle fire, camp fire". This records what was built and what's still open.

## Short Description

The Simulated Fire gets AquaSuite's simulation-preset mechanism, with three presets: **Normal Fire**, **Candle Fire** and **Campfire**. A preset is plain data and an editable starting point: it's chosen at Create (in the redo panel) or applied later from the effect box's Preset menu and Apply button. The effect stores what was applied, and says "(modified)" once anything no longer matches, whether the edit was made in the add-on's panel or Blender's Physics panel. Saved scenes keep values, never a reference to the live definitions.

## How AquaSuite does it, and what was kept

AquaSuite's `core/presets.py`:

- A `CATALOG` of packages built by `_package`.
- `ITEMS` for Create, and `CHOICES` for the menu, with Custom at 0.
- `apply(context, entry, preset_id)`, which writes the package once inside an `applying` guard. It stores a JSON snapshot plus the preset's id, label, menu choice and modified flag.
- `is_modified` and `note_edit`, called from property updates and from a `depsgraph_update_post` watch.
- A decoded-snapshot cache that's reset on load, undo and redo.
- An Apply operator.

The add-on's `effects/sim_presets.py` mirrors each of these. The differences:

- **Field names.** The entry's fields are `sim_preset`, `sim_preset_label`, `sim_preset_choice`, `sim_preset_snapshot` and `sim_preset_modified`, because `preset_id` already holds the Add preset's id.
- **Create.** `sim_fire.create_sim_fire` builds the structure, then calls `apply`, so Create and Apply share one path.
- **Applying a preset.** Apply reshapes the domain and emitter meshes in place, so names, tags and materials stay. It moves the emitter and light, writes the domain, flow, volume and light values, and puts Flame Intensity, Smoke Amount and Light Strength back to 1 and Detail to the preset's. Then it clears the Replay cache.
- **The snapshot** covers Detail, the three sliders, the domain's resolution and the package's domain and flow fields. The light mode is the buyer's own choice and isn't tracked.

## Architectural decisions

- **The Add preset.** `SIMULATED_CAMPFIRE` keeps its id and number 8, and is now labelled **Simulated Fire**, since it offers three fires.
- **Default.** With no choice, Create makes the Campfire, with REQ-002's values unchanged.
- **Fixed numbers.** The simulation presets are Normal Fire 1, Candle Fire 2 and Campfire 3, with Custom 0. They're saved in files, so they're fixed for good.
- **Object names.** Each preset names its objects: Simulated Fire, Simulated Candle or Simulated Campfire. A later Apply doesn't rename anything.

## Acceptance Criteria

- [x] **AC1.** Create offers the three presets and builds each one as its package says. Each one burns on 4.5 and 5.2 (`tests/test_sim_presets.py`).
- [x] **AC2.** Apply turns one preset into another on the same owned objects, resets the sliders and makes the next play simulate the new fire.
- [x] **AC3.** Any edit marks the preset "(modified)": the sliders, Detail, or the domain or emitter edited directly. Apply clears it.
- [x] **AC4.** A changed definition never changes or marks a fire already made. The applied preset and its snapshot survive saving and opening.
- [x] **AC5.** Only a Simulated Fire takes a simulation preset. Custom can't be applied. Both refusals are plain sentences.
- [x] **AC6.** Each preset's first play-through runs at 5 fps or more in a windowed EEVEE viewport on 4.5.4 and 5.2.2 (`docs/LOOK_TEST.md`).
- [ ] **AC7.** The owner's Cycles verdict on Normal Fire and Candle Fire is recorded in `docs/LOOK_TEST.md`.
- [ ] **AC8.** Everything above is checked on 5.1, which isn't installed on this PC.

## Open Questions

- **Q1.** Are Normal Fire and Candle Fire the looks the owner wants? They're proposed by render (see `docs/LOOK_TEST.md`). The Candle's flame shows faint banding.
- **Q2.** Should the Add panel offer the three directly, as buttons or a menu? Today they're in the redo panel and the effect box, as in AquaSuite.

## Revision History

| Date | Author | Summary of Change |
| ---- | ------ | ----------------- |
| 2026-11-04 | Blaxine | Built and recorded. Open: AC7 (the owner's look verdict) and AC8 (5.1). |
