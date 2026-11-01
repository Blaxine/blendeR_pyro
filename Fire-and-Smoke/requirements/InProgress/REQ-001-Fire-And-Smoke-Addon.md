# REQ-001 — Fire and Smoke Add-on

| Field | Value |
| ----- | ----- |
| ID | REQ-001 |
| Title | Fire and Smoke Add-on |
| Status | InProgress |
| Phase | New product, pre-1.0 |
| Tier | Major feature |
| Area | Whole add-on: Geometry Nodes plane stacks, materials, fire light, view sync, ownership and delete, embers, panel, presets, release |
| Author | Blaxine |
| Created | 2026-11-01 |
| Last Updated | 2026-11-01 |

> Source PRD: REQ-001-PRD-Fire-And-Smoke-Addon.md

> Grilled from `Fire-and-Smoke-Addon-Plan.md` in the repo root. Where the two differ, this plan wins for implementation: see Constraints and the resolved Open Questions.

## Short Description

A new paid Blender add-on for beginners, sold separately from AquaSuite. It adds fire, smoke, smoke columns and embers from 8 presets in a simple panel. Flames and smoke are stacks of camera-facing planes with animated procedural noise, built with Geometry Nodes, so they scrub with no baking. It works in Cycles and EEVEE on Blender 4.5, 5.1 and 5.2.

The work starts with one Campfire and a look test. No later slice starts until the owner has passed that test by eye, and a second failure stops the project.

## User Stories

1. As a Blender beginner, I want to add fire, smoke, a smoke column or embers from a preset in a simple panel that tells me clearly when something can't be done, so that I get a believable effect without learning how it's made
2. As a Blender beginner, I want to set one of my own meshes on fire without my object being changed, so that I can burn something in my scene and still keep the original intact
3. As a Blender beginner, I want flames and smoke to scrub instantly and keep facing me as I move around the viewport, with final renders always facing the scene camera, so that I can work on my shot without waiting and a forgotten preview setting can't waste a render
4. As a Blender beginner, I want my fire to cast flickering light that looks the same in Cycles and EEVEE, so that it feels part of the scene whichever engine I use
5. As a Blender beginner, I want deleting an effect to remove only what the add-on made for that effect, even in copied scenes or after I've changed things myself, so that cleaning up never destroys my work

## Constraints

Measured on Blender 5.1.2 and 5.2.3 on this PC on 2026-11-01. Blender 4.5 isn't installed, so nothing here is measured on it yet.

- **Geometry Nodes can't read the viewport from a modifier, on any tested version.** Viewport Transform raises `Node must be run as tool` there, and the 4.5 and 5.1 manuals both limit it to the Tool context. Is Viewport, Active Camera and Camera Info all work in a modifier.
- **Cycles draws solid black where a ray crosses as many planes as `cycles.transparent_max_bounces` (default 8).** 8 planes at limit 8 and 16 at limit 16 fail; 7 at 8, 8 at 16 and 24 at 32 are clean. `max_bounces` stayed at 12 throughout. EEVEE isn't affected. The property's hard maximum is 1024.
- **Planes change the scene's lighting unless hidden from those rays.** Mean red brightness, EEVEE and Cycles: default visibility 0.134 and 0.183; shadow off 0.203 and 0.239; shadow, diffuse and glossy off 0.2034 and 0.2057.
- **Final renders ignore the view target.** With Is Viewport choosing between view target and camera, a render with the target side-on and one with it at the camera differed by 0.00000 per pixel in EEVEE. In the headless viewport-mode depsgraph, the instances faced the target.
- **The 3x Cycles target is tight against an empty frame.** Against a near-empty frame at 640×360 and 32 samples, 8 planes cost 2.5 to 2.7x, 16 about 3.9x and 24 about 5x. The first EEVEE render includes shader compilation (an empty frame took 1.19 s on 5.1 and 15.99 s on 5.2), so timings must discard it.
- **Plane evaluation is cheap.** With 8 planes, `frame_set` averaged 0.23 to 0.25 ms, and moving the view target and reading the result took about 6 ms.
- **Headless runs can't test everything.** `-b` runs have no windows, so the view sync timer, viewport frame rate and panel appearance need a person in a window.
- **Some AquaSuite code must not be copied as it stands.** `core/lighting.py:65` restores settings unconditionally and checks only the world. `core/delete.py:186` shares a copied scene's uuid and has no new-ID logic. No AquaSuite Python file uses `BLENDER_USER_RESOURCES`.
- **The manifest can't exclude Blender 5.0.** It offers only a minimum and maximum version, so a 4.5 minimum also allows 5.0 to install.
- **`Blaxine/blendeR_pyro` is public today.** GitHub's API returned 200 without a login. Blender 5.2 is already installed, so only 4.5 is missing. Add-ons that use `bpy`, and code copied from AquaSuite, are GPL-3.0-or-later, so buyers may legally redistribute the zip.

## Architectural decisions

- **Repo layout:** `blendeR_pyro` is the private code repo. `Fire-and-Smoke/` is the add-on root: manifest, `__init__.py`, `tests/`, `docs/` and `requirements/` all sit there.
- **Working identity:** manifest id `fire_and_smoke`, property and datablock prefix `fas_`, with the display name in one constant. All three are final before the store page and issues repo exist.
- **Effect:** the unit of creation and deletion, tracked in `Scene.fas_effects` and tagged on every ID it creates with `fas_owner = "<kind>:<uuid>"`. Each entry stores the add-on version and a data version.
- **Plane stack:** a Geometry Nodes instance stack, spinning around the vertical axis only. Each instance stores `fas_layer` and `fas_time`, and the material reads them through Instancer-type Attribute nodes.
- **Facing rule:** `Is Viewport AND Face Viewport` selects the view target; anything else selects the Active Camera. Face Viewport is a modifier input, labelled preview-only.
- **View sync:** one Python timer finds the 3D viewport whose view changed most recently and writes its position to a per-scene, add-on-owned view target empty. The target reaches each effect through an Object modifier input. The timer writes only when the view has moved, and never during a render job.
- **Fire light:** one owned point light per fire effect, flickering through a Noise F-curve modifier on `energy`, with no drivers or handlers. Light mode is per effect: Real (default), Emissive or Both.
- **Plane visibility:** planes never cast shadows. In Real mode they are also hidden from diffuse and glossy rays; Emissive and Both turn those rays back on.
- **Bounce limit:** when creating an effect, if `transparent_max_bounces` is at or below the scene's total planes across all effects, raise it to that total plus one, capped at 1024, and report it. The scene records the original and the value set. Deleting lowers or restores it only while it still equals the value set.
- **Fire on a mesh:** a separate owned object that reads the source mesh. The buyer's object gets no modifier, tag or data change.
- **Embers:** a legacy particle system on an owned emitter, following timeline changes.
- **Presets:** plain data applied once. The stored list only grows at the end, with display order sorted separately. Preset choices and delete options use `SKIP_SAVE`.
- **AquaSuite reuse:** copy each piece once when a slice needs it, and rename its prefixes. No shared package.
- **Dependencies and license:** Blender's built-in modules only, no network access, GPL-3.0-or-later. The manifest has no `website` until the public issues repo exists.

## UI / UX Notes

- **Before slice 8:** no panel. The Campfire is created from F3 search, and settings are changed in the Modifiers tab.
- **Panel:** 3D Viewport N-panel with the Simple and Advanced approach from AquaSuite: preset choice, Create, a box per effect, Delete and short hints.
- **Fixed wording:** the facing switch is labelled preview-only and states that final renders always face the scene camera. The Emissive option notes that it is Cycles-focused.
- **Reports:** creating an effect reports any raise of the bounce limit. Deleting reports a restore, or that the limit was left alone because it had changed.
- **Error states, each with a plain message and no traceback:** no scene camera; no mesh selected for fire on a mesh; source mesh deleted; source too dense.

## Acceptance Criteria

- [ ] **AC1 — Look gate.** In the committed test scene, with a mid-ground orbiting camera, the owner watches Campfire clips rendered in Cycles and EEVEE on 5.2 and records pass or fail in `docs/LOOK_TEST.md`, with the clips and numbers. A fail allows one more round, which may add grayscale masks. A second fail stops the project. No later slice starts without a recorded pass.
- [ ] **AC2 — Speed target confirmed.** The default Campfire's EEVEE viewport frame rate and its Cycles cost against an empty 1080p frame are measured on this PC, and the target is confirmed or changed in `docs/LOOK_TEST.md`.
- [ ] **AC3 — Install and upgrade.** The built zip validates, installs into a temporary user folder and creates a Campfire on every promised Blender. Installing over a turned-off version runs the new code.
- [ ] **AC4 — No black planes.** With factory settings, a new effect renders in Cycles with no black rectangles, including two effects lined up from the camera.
- [ ] **AC5 — Renders face the camera.** A final render faces the scene camera whatever the switch and viewport are doing.
- [ ] **AC6 — Preview switch.** With Face Viewport on, planes follow the most recently moved viewport as it orbits, in a window, on all promised Blenders. With Face Camera, they stay on the scene camera.
- [ ] **AC7 — Steep angles.** From steep angles, planes fade to a low glow and never show as thin slices or a flat card.
- [ ] **AC8 — Light options.** Each fire effect offers Real, Emissive and Both, with Real as default. The flicker changes over frames with no Python running, and Real looks the same in both engines by eye.
- [ ] **AC9 — Safe delete.** Delete removes only IDs tagged for that effect, even after renames. Anything the buyer adopted, and anything the buyer changed afterwards, stays.
- [ ] **AC10 — Copied scenes.** Effects in a copied scene get a new ID, and deleting one in either scene leaves the other working.
- [ ] **AC11 — Bounce limit restored.** Deleting the last effect restores the original limit if it still equals the value set, and otherwise leaves it alone.
- [ ] **AC12 — Smoke.** Smoke on a point and smoke columns scrub with no bake and match by eye in both engines.
- [ ] **AC13 — Fire on a mesh.** Fire follows a chosen mesh, including when it moves, and the source object's modifiers, mesh and custom properties are unchanged. Deleted and over-dense sources give a clear message.
- [ ] **AC14 — Embers.** Embers render in both engines, replay from the start when scrubbed, and follow timeline changes unless the buyer set their own range.
- [ ] **AC15 — Panel.** A beginner can create and delete every effect kind from the panel in Simple view, every failure gives a plain message, and the fixed wording appears.
- [ ] **AC16 — 8 presets.** The final 8 presets each create without error and pass the eye check. Adding a preset to the end of the list doesn't change what a saved choice means.
- [ ] **AC17 — Name and links.** The add-on is named, its id and prefix are final, and every support link in the zip points at a public issues repo that already exists.
- [ ] **AC18 — Store page.** The store text states every limit in the plan: mid-ground use, no extreme close-ups, weak top-down shots, embers replaying, "no baking" limited to flames and smoke, the engine match limited to the default light, and the three supported versions.
- [ ] **AC19 — Release gate.** A version ships only when, for that version: the owner has viewed and rendered all 8 presets in both engines on 5.1 and 5.2 (32 checks); 4.5 has passed automated tests, one render per preset and the owner's scripted beginner walkthrough; automated tests pass on all versions; the built zip has been installed and tested; and the default Campfire meets the confirmed speed target.

## Technical Notes

**Paths** are relative to `Fire-and-Smoke/`. New files are named only where the plan fixes them. Everything else takes its name from the code that lands first.

**AquaSuite copy sources** (`C:\Users\User\Downloads\blender_aqua`):

| Need | Source | Note |
| ---- | ------ | ---- |
| Module clearing, register retry, operator guard | `__init__.py:17-21`, `:45-56`, `:61-65` | Clearing is required from the first commit |
| Manifest and build excludes | `blender_manifest.toml` | Drop `website` and the cache permission; set `blender_version_min = "4.5.0"` |
| Test runner and helpers | `tests/run_tests.py`, `tests/aqs_testlib.py` | Each test file runs in a fresh `-b --factory-startup` process, with paths from `tests/blender_paths.local.json` |
| Install and upgrade tests | `tests/test_package.py`, `tests/test_upgrade.py` | Add a temporary `BLENDER_USER_RESOURCES` to every install test |
| Tagging | `core/naming.py:19-33` | `owned_by` matches on the uuid suffix |
| Delete and create rollback | `core/delete.py:199-225`, `:228-269`, `:291-320` | Sweep lights and actions too, and add new-ID handling |
| Errors and busy check | `core/errors.py`, `_busy` at `:152` | Use `_busy` to skip view sync during render jobs |
| Timeline following | `core/handlers.py:127-168` | A range the buyer set stays theirs |
| Settings restore shape | `core/lighting.py:53-68` | Compare the current value before restoring |
| Simple and Advanced panel | `ui/control_spec.py`, `ui/panel.py:656`, `:678-751` | Use a new N-panel category |
| Panel and ownership tests | `tests/test_simple_view.py`, `tests/test_ownership.py`, `tests/test_create_delete.py` | Hold uuids, never entry objects |
| `SKIP_SAVE` and render method | `level2/still_water.py:480`, `materials/mats.py:217-219` | |

**Plane stack recipe, built and rendered on 5.1 and 5.2:**

- Object Info in Relative mode gives the camera or view target in the object's space. Facing angle: `atan2(x, -y)`, applied as the Z rotation on Instance on Points.
- Points: Mesh Line, then Set Position with an offset along the flattened view direction, by `(index - (count - 1) / 2) * spacing`.
- Plane: 2×2 Grid with its UV Map output stored as `UVMap` on the corner domain, then Transform upright, then Set Material.
- After instancing, store `fas_layer` (index over last index) and `fas_time` (Scene Time seconds) on the Instance domain.
- Material: an Attribute node in Geometry mode for `UVMap`, two in Instancer mode for `fas_layer` and `fas_time`. 4D Noise takes the scrolled UV with layer depth as Vector, and time as W. A Mix Shader joins Transparent and Emission.
- Set `surface_render_method` on the material. `BLENDED` and `DITHERED` both rendered; the smoke choice is made in the look test.

**Other measured details:**

- **Flicker path:** `light.keyframe_insert("energy", frame=1)`, then `action.layers[0].strips[0].channelbag(anim.action_slot).fcurves[0].modifiers.new("NOISE")`. The values were identical on 5.1 and 5.2. Tag the light data and the action for the effect.
- **Object visibility:** `visible_shadow`, `visible_diffuse` and `visible_glossy` on the object drive both engines.
- **Viewport data:** `SpaceView3D.region_3d`, `SpaceView3D.region_quadviews` and `RegionView3D.view_matrix`, `view_location`, `view_perspective` and `is_perspective` all exist on 5.2. Test for the presence of `scene.cycles` before reading the limit.
- **EEVEE identifier:** `BLENDER_EEVEE` on 5.1 and 5.2. Expected to be `BLENDER_EEVEE_NEXT` on 4.5, so tests read it from the engine enum.

**Tests** follow AquaSuite's pattern: `tests/test_<area>.py` with `test_*` functions, ending in the helper's `main(globals())`. Run with `python tests/run_tests.py` from `Fire-and-Smoke/`.

## Implementation Steps

| Phase | Meaning |
| ----- | ------- |
| F | Foundation |
| S | Service: node trees, materials, operators, handlers |
| U | UX |
| D | Docs |
| T | Tests |
| O | Owner action, done by hand |
| X | Release and cross-document work |

### Slice 1 — Campfire and look gate

**Demoable when:** F3 search creates a Campfire on every promised Blender, and `docs/LOOK_TEST.md` holds a recorded verdict with clips and speed numbers.
**Satisfies:** AC1, AC2, AC3 · **Covers:** none in full; this slice decides whether the rest gets built

| Done | # | Phase | Title | Description | Depends on | Primary files |
| ---- | - | ----- | ----- | ----------- | ---------- | ------------- |
|  | S001 | O | Make the repo private | Switch `Blaxine/blendeR_pyro` to private before any add-on code is committed. Confirm that GitHub's API returns 404 without a login. | — | GitHub settings |
|  | S002 | O | Install Blender 4.5 | Install 4.5 LTS beside 5.1 and 5.2, and rerun the measured checks in Constraints on it. Anything that differs goes in `docs/LOOK_TEST.md`. | — | `tests/blender_paths.local.json` |
| ✅ | S003 | F | Scaffold the extension | Manifest with the working id, 4.5 minimum and build excludes for `requirements/`, `tests/`, `docs/THESAURUS.md`, `docs/LOOK_TEST.md` and `docs/RELEASE_CHECKLIST.md`. `__init__.py` with module clearing. One display-name constant. `.gitignore`. | S001 | `blender_manifest.toml`, `__init__.py`, `.gitignore` |
| ✅ | S004 | T | Bring over the test runner | Copy and rename the runner and helper, with the `FAS_TEST` tag and the three Blender paths in the example config. | S003 | `tests/run_tests.py`, test helper |
| ✅ | S005 | S | Build the Campfire plane stack | The node tree from Technical Notes with hard-coded Campfire values, always facing the Active Camera. The object is hidden from shadow, diffuse and glossy rays. | S003 | add-on package |
| ✅ | S006 | S | Build the flame material | Noise-driven emission and transparency reading the instance attributes, with no images. | S005 | add-on package |
| ✅ | S007 | S | Add the flickering light | An owned point light with the Noise F-curve modifier on `energy`. | S005 | add-on package |
| ✅ | S008 | S | Add the Create operator | One operator, found through F3, that creates the Campfire at the 3D cursor and raises the bounce limit using the rule in Architectural decisions. No restore yet. | S005, S006, S007 | add-on package |
| ✅ | S009 | T | Test the Campfire | New `tests/test_campfire.py`: no modifier warnings; instances face the camera after it moves; bounce limit above plane count; pixels differ between frames; no black rectangle in Cycles at factory settings. | S008, S004 | `tests/test_campfire.py` |
| ✅ | S010 | T | Test install and upgrade | Copy `tests/test_package.py` and `tests/test_upgrade.py`, cut down to one operator, with `BLENDER_USER_RESOURCES` pointing at a temp folder for every install. | S002, S004, S008 | `tests/test_package.py`, `tests/test_upgrade.py` |
| ✅ | S011 | F | Script the look test | A committed script that builds the test scene (ground, orbiting mid-ground camera, no `.blend` file) and renders clips in both engines. It also renders a rough smoke stack with both shading options, and shows the base of the planes on the ground. | S008 | `docs/LOOK_TEST.md`, script under `tests/` |
|  | S012 | O | Measure speed | Read the default Campfire's frame rate in an EEVEE viewport in a window. The script measures Cycles against an empty 1080p frame, discarding first-render compile time. Confirm or change the target. | S011 | `docs/LOOK_TEST.md` |
|  | S013 | O | Judge the look: round 1 | Watch the clips in both engines and record pass or fail, the smoke shading choice and the ground-line decision. | S011, S012 | `docs/LOOK_TEST.md` |
|  | S014 | S | Round 2, only after a fail | Add a few grayscale shape masks, which drops the "no images" rule and adds art and licensing work, then repeat S011 to S013. A second fail stops the project: record that and start no further slices. | S013 | add-on package, `docs/LOOK_TEST.md` |
| ✅ | S015 | D | Add new terms to the thesaurus | Add Effect, Plane stack, View sync, View target, Look test, Release gate, Light mode and Bounce limit to `docs/THESAURUS.md`. | S013 | `docs/THESAURUS.md` |

### Slice 2 — Facing, preview switch and view sync

**Demoable when:** orbiting a viewport makes the planes follow with Face Viewport on, and a render from a different angle still faces the scene camera.
**Satisfies:** AC5, AC6, AC7 · **Covers:** US3

| Done | # | Phase | Title | Description | Depends on | Primary files |
| ---- | - | ----- | ----- | ----------- | ---------- | ------------- |
|  | S016 | S | Prove view sync on 4.5 | A minimal timer that writes the viewport position to an empty, run in a window on 4.5, 5.1 and 5.2 before anything else in this slice. If it fails on 4.5, resolve Q4 first. | S013 | add-on package |
| ✅ | S017 | S | Add the facing rule | The Face Viewport modifier input and the view target input, wired as in Architectural decisions. | S016 | add-on package |
| ✅ | S018 | S | Build the view sync | Scan every window's 3D viewports including quad views, take the most recently changed view, and write only on movement. Skip during render jobs. Register and unregister cleanly, and survive file loads. | S017 | add-on package |
| ✅ | S019 | S | Add the steep-angle fade | Fade planes to a low glow as the viewing angle steepens, on the plane stack and in the material. | S017 | add-on package |
| ✅ | S020 | S | Settle the edge cases | Decide and build what viewport renders face (Q5) and what happens with no scene camera (Q6), with a plain message for the latter. | S017 | add-on package |
| ✅ | S021 | T | Test facing | New `tests/test_facing.py`: the render ignores a side-on view target; the viewport-mode depsgraph follows the target with the switch on and the camera with it off; the view-position write works without a window; register and unregister leave no timer. | S018, S019, S020 | `tests/test_facing.py` |
|  | S022 | O | Eye check in a window | Orbit on all three Blenders, in single and multiple viewports. Check lag, the steep-angle fade and playback. | S018, S019 | `docs/LOOK_TEST.md` |

### Slice 3 — Light options

**Demoable when:** switching a Campfire between Real, Emissive and Both changes how the ground is lit, and Real looks the same in both engines.
**Satisfies:** AC8 · **Covers:** US4

| Done | # | Phase | Title | Description | Depends on | Primary files |
| ---- | - | ----- | ----- | ----------- | ---------- | ------------- |
| ✅ | S023 | S | Add light modes | A per-effect mode that shows or hides the owned light and sets the plane ray visibility from Architectural decisions. | S013 | add-on package |
| ✅ | S024 | T | Test light modes | New `tests/test_light.py`: visibility flags per mode; flicker changes over frames with handlers absent; Real's mean brightness stays close across engines, using the measured 0.2034 and 0.2057 as the reference. | S023 | `tests/test_light.py` |
|  | S025 | O | Compare engines by eye | Compare Real in both engines in the look test scene on 5.1 and 5.2. | S023 | `docs/LOOK_TEST.md` |

### Slice 4 — Create, delete, ownership and copied scenes

**Demoable when:** Delete removes a Campfire and restores the bounce limit, a renamed part still goes, and a copied scene survives deletion in its source.
**Satisfies:** AC4, AC9, AC10, AC11 · **Covers:** US5

| Done | # | Phase | Title | Description | Depends on | Primary files |
| ---- | - | ----- | ----- | ----------- | ---------- | ------------- |
| ✅ | S026 | S | Add effect records | Copy tagging, the `Scene.fas_effects` registry, version stamps and create rollback, and tag every ID an effect creates, including the light data and action. | S013 | add-on package |
| ✅ | S027 | S | Add errors and operator guard | Copy the error pipeline, so no operator fails with a raw traceback. | S026 | add-on package |
| ✅ | S028 | S | Add the Delete operator | Delete only by owner tag, within this scene's effect. Release anything adopted elsewhere. Delete options use `SKIP_SAVE`. Remove the view target with the scene's last effect. | S026 | add-on package |
| ✅ | S029 | S | Give copied effects new IDs | Detect a scene copy's shared uuid and give that copy its own ID and tags before any delete acts on it. Confirm the view target input points at the copy's own target. | S028 | add-on package |
| ✅ | S030 | S | Track the bounce limit | The full rule from Architectural decisions, with the fire light following the same "only if it's still ours" check. | S028 | add-on package |
| ✅ | S031 | T | Test ownership | New `tests/test_create_delete.py`, `tests/test_ownership.py` and `tests/test_copied_scene.py`: renames; user-adopted data; failed create leaves nothing; both directions of copied-scene delete; bounce limit restored, and left alone if changed; two fires lined up from the camera render without black. | S029, S030 | listed files |

### Slice 5 — Smoke on a point and smoke columns

**Demoable when:** both smoke kinds scrub with no bake and read as smoke in both engines.
**Satisfies:** AC12 · **Covers:** US1 (smoke)

| Done | # | Phase | Title | Description | Depends on | Primary files |
| ---- | - | ----- | ----- | ----------- | ---------- | ------------- |
| ✅ | S032 | S | Generalise the plane stack | Parameterise the stack so each effect kind sets size, count, spacing and scroll speed. Fire must not change appearance. | S026 | add-on package |
| ✅ | S033 | S | Build the smoke material | The shading and render method chosen in S013, with no fire light. | S032 | add-on package |
| ✅ | S034 | S | Add smoke kinds | Create operators for smoke on a point and smoke columns. | S033 | add-on package |
| ✅ | S035 | T | Test smoke | New `tests/test_smoke.py`: create and delete; pixels differ between frames; no black in Cycles; Campfire values unchanged. | S034 | `tests/test_smoke.py` |
|  | S036 | O | Compare smoke by eye | Check both kinds in both engines on 5.1 and 5.2. | S034 | `docs/LOOK_TEST.md` |

### Slice 6 — Fire on a mesh

**Demoable when:** a chosen mesh burns and follows its movement, its own data is unchanged, and deleting either side behaves clearly.
**Satisfies:** AC13 · **Covers:** US2

| Done | # | Phase | Title | Description | Depends on | Primary files |
| ---- | - | ----- | ----- | ----------- | ---------- | ------------- |
| ✅ | S037 | S | Build the mesh fire object | A separate owned object that reads the source and places plane stacks across its surface, with no change to the source. | S032 | add-on package |
| ✅ | S038 | S | Place its light | Decide and build the light position for mesh fires (Q7). | S037 | add-on package |
| ✅ | S039 | S | Set limits and handle a missing source | Measure dense and deforming meshes on this PC, then set the limit and the behaviour for a deleted source (Q8), each with a plain message. | S037 | add-on package |
| ✅ | S040 | T | Test mesh fire | New `tests/test_mesh_fire.py`: the source's modifiers, mesh and custom properties are identical before, during and after; it follows a moved source; deleted source and over-limit cases; delete leaves the source intact. | S038, S039 | `tests/test_mesh_fire.py` |
|  | S041 | O | Check mesh fire by eye | Check both engines on 5.1 and 5.2, with a simple and a dense mesh. | S038 | `docs/LOOK_TEST.md` |

### Slice 7 — Embers

**Demoable when:** embers rise from a fire in both engines and follow a changed timeline.
**Satisfies:** AC14 · **Covers:** US1 (embers)

| Done | # | Phase | Title | Description | Depends on | Primary files |
| ---- | - | ----- | ----- | ----------- | ---------- | ------------- |
| ✅ | S042 | S | Build the ember emitter | A legacy particle system on an owned emitter, with an owned instance object and material, tagged for delete. | S026 | add-on package |
| ✅ | S043 | S | Follow the timeline | Copy the range handling, keeping a range the buyer set. | S042 | add-on package |
| ✅ | S044 | T | Test embers | New `tests/test_embers.py`: create and delete leave no particle settings behind; range following, and a buyer-set range staying put; particles exist after a frame change. | S043 | `tests/test_embers.py` |
|  | S045 | O | Check embers by eye | Check both engines on 5.1 and 5.2, and confirm the replay-from-start behaviour when scrubbing. | S043 | `docs/LOOK_TEST.md` |

### Slice 8 — Panel and 8 presets

**Demoable when:** a beginner can make and delete all 8 presets from the panel alone.
**Satisfies:** AC15, AC16 · **Covers:** US1

| Done | # | Phase | Title | Description | Depends on | Primary files |
| ---- | - | ----- | ----- | ----------- | ---------- | ------------- |
| ✅ | S046 | U | Build the panel | Simple and Advanced views, Create, a box per effect, Delete, hints, the fixed wording and error messages. | S030, S034, S037, S042 | add-on package |
| ✅ | S047 | S | Define the preset list | Final list of 8 (Q3), as plain data with an append-only stored list and separate display order. Preset choices use `SKIP_SAVE`. | S046 | add-on package |
| ✅ | S048 | T | Test panel and presets | New `tests/test_panel.py` and `tests/test_presets.py`: panels draw on a stand-in layout, as in `tests/test_simple_view.py`; each preset creates and deletes; stored values keep their meaning when a preset is added; `SKIP_SAVE` is set. | S047 | listed files |
|  | S049 | O | Eye check every preset | Check all 8 in both engines on 5.2. Replace any preset that fails. | S047 | `docs/LOOK_TEST.md` |

### Slice 9 — Name, issues repo, links and store text

**Demoable when:** the zip carries the final name and working support links, and the store text is ready.
**Satisfies:** AC17, AC18 · **Covers:** none

| Done | # | Phase | Title | Description | Depends on | Primary files |
| ---- | - | ----- | ----- | ----------- | ---------- | ------------- |
|  | S050 | O | Choose name and price | Choose the add-on's name (Q1) and price (Q2). | S049 | — |
|  | S051 | F | Finalise identity | Update the display name, manifest id and prefix if they change, and confirm the suite still passes. Scenes saved under the working id aren't migrated. | S050 | `blender_manifest.toml`, add-on package, `tests/` |
|  | S052 | O | Create the public issues repo | Create it with an issues-only README before any link is written. | S050 | GitHub |
|  | S053 | U | Add support links | Add the manifest `website`, panel links and bug-report text, all pointing at the issues repo. | S052, S051 | `blender_manifest.toml`, add-on package |
|  | S054 | T | Test links | Extend `tests/test_package.py`: the zip contains no link to the private repo, and shipped files exclude plans, tests and internal docs. | S053 | `tests/test_package.py` |
|  | S055 | D | Write buyer docs and store text | README, troubleshooting and store text stating every limit in AC18. | S053 | `README.md`, `docs/` |

### Slice 10 — Release gate

**Demoable when:** the release run refuses a version with any open box, then passes once all are ticked.
**Satisfies:** AC19 · **Covers:** none

| Done | # | Phase | Title | Description | Depends on | Primary files |
| ---- | - | ----- | ----- | ----------- | ---------- | ------------- |
|  | S056 | D | Write the checklist | One box per AC19 item for the version under test, including the 32 eye checks and the scripted 4.5 walkthrough: install, add a preset, set a mesh on fire, render, delete. | S055 | `docs/RELEASE_CHECKLIST.md` |
|  | S057 | T | Enforce the gate | A `--release` option on the test runner that fails unless the checklist names the manifest version and has no open box. | S056 | `tests/run_tests.py` |
|  | S058 | O | Run the gate | Complete every box, then run `python tests/run_tests.py --release` on all versions. | S057 | `docs/RELEASE_CHECKLIST.md` |
|  | S059 | X | Launch | Build the final zip, publish the store page, and move this plan and its PRD to `requirements/Done/`. | S058 | `requirements/` |

### Dependency graph

```
S001 → S003 → S004, S005                                    Slice 1
S005 → S006, S007 → S008
S004, S008 → S009
S002, S004, S008 → S010
S008 → S011 → S012 → S013 → S014 (only after a fail), S015

S013 → S016 → S017 → S018, S019, S020 → S021, S022         Slice 2
S013 → S023 → S024, S025                                    Slice 3
S013 → S026 → S027, S028 → S029, S030 → S031                Slice 4
S026 → S032 → S033 → S034 → S035, S036                      Slice 5
S032 → S037 → S038, S039 → S040, S041                       Slice 6
S026 → S042 → S043 → S044, S045                             Slice 7
S030, S034, S037, S042 → S046 → S047 → S048, S049           Slice 8
S049 → S050 → S051, S052 → S053 → S054, S055                Slice 9
S055 → S056 → S057 → S058 → S059                            Slice 10
```

## Dependencies

| REQ ID | Title | Reason |
| ------ | ----- | ------ |
| — | AquaSuite (`blender_aqua`, separate repo) | Source for code copied once; no runtime dependency |

**Supersedes:** `Fire-and-Smoke-Addon-Plan.md` for implementation. `AquaSuite_PYRO_Fire_TDD.md` in Downloads, an older Mantaflow design for fire inside AquaSuite, isn't used.

## Out of Scope

- End-to-end or GUI-driven test automation. Anything needing a window goes on the eye-check list.
- Migration for scenes saved under the working id.
- Blocking installation on Blender 5.0, or testing on it.
- Eye checks on 4.5 beyond the renders and the scripted walkthrough.
- Backporting fixes between this add-on and AquaSuite.
- A shared code package with AquaSuite.
- Tuning the look of any effect other than the Campfire before the look gate passes.
- Store setup and payment processing beyond the store text.

## Open Questions

- [x] **Q-A — Resolved.** `blendeR_pyro` stays the code repo and goes private before any add-on code is committed. *(Blaxine)*
- [x] **Q-B — Resolved.** The add-on root is `Fire-and-Smoke/`. *(Blaxine)*
- [x] **Q-C — Resolved.** This plan covers the whole product, with the look test as a hard gate in slice 1. *(Blaxine)*
- [x] **Q-D — Resolved.** The prototype is an installable extension with one operator, with no panel or presets. *(Blaxine)*
- [x] **Q-E — Resolved.** Face Viewport uses a Python view sync. This replaces the plan's open question about whether the node works on 4.5, since the node fails in modifiers on every version tested. *(Blaxine)*
- [x] **Q-F — Resolved.** AquaSuite code is copied once and adapted, with no shared package. *(Blaxine)*
- [x] **Q-G — Resolved.** The look test uses a fixed scene and moving shot, judged by the owner, with a written record. *(Blaxine)*
- [x] **Q-H — Resolved.** The 4.5 "beginner session" is the owner following a scripted walkthrough. *(Blaxine)*
- [x] **Q-I — Resolved.** The add-on raises the bounce limit, tracks it and restores it. *(Blaxine)*
- [ ] **Q1 — Add-on name.** What is the add-on called? Deferred until slice 9 starts, before the store page and issues repo. The plan's "before creating the repos" no longer applies, since the code repo exists.
- [ ] **Q2 — Price.** What does it cost? Deferred until the look test passes; set in S050.
- [ ] **Q3 — Exact preset list.** Built as Candle, Torch, Campfire, Bonfire, Burning Object, Thin Smoke, Black Smoke Column and Embers. Deferred until the owner's eye check in S049; replace any that fail.
- [ ] **Q4 — View sync on 4.5.** If the view sync fails on 4.5, does 4.5 go without the switch, or does the promise change? Deferred until S016 shows a failure.
- [x] **Q5 — Resolved.** Viewport renders are viewport evaluations, so they follow the switch; a moving camera should use Face Camera for them. *(Claude, for owner review)*
- [x] **Q6 — Resolved.** Planes still evaluate and hold their last sensible direction, Face Viewport keeps working, Create warns, and the panel says the scene needs a camera before rendering. *(Claude, for owner review)*
- [x] **Q7 — Resolved.** Above the top of the mesh's bounding box, following it through a constraint on the light. Inside a closed mesh a light lights nothing. *(Claude, for owner review)*
- [x] **Q8 — Resolved.** Measured on 5.2: 4 ms per frame at 200,000 faces, 15 ms at 1,000,000. Over 500,000 faces warns, over 2,000,000 refuses. A deleted source leaves no planes and no errors, and the effect can still be deleted. Deforming meshes add their own cost on top, which isn't measured. *(Claude, for owner review)*
- [x] **Q9 — Resolved.** Smoke carries its own shading, using the Blended render method, so it matches in both engines (mean pixel difference 0.001 to 0.004). It doesn't pick up scene lights or a nearby fire's colour. *(Claude, for owner review)*
- [x] **Q10 — Resolved, pending the owner's eye.** Flames fade out at their base, which hides the ground line, and mesh fires stand clear of the mesh towards the viewer, which removes the hard cuts. *(Claude, for owner review)*
- [ ] **Q11 — Legacy particles.** Do embers stay on legacy particles? Deferred until a supported Blender release deprecates them.

## Smoke Test

> Developer runs the app; the agent does not self-run.

**After slice 1:**

1. Run `python tests/run_tests.py` from `Fire-and-Smoke/`. It should pass on 4.5, 5.1 and 5.2.
2. Build the zip and install it in Blender 5.2 with a clean profile.
3. In a new file, press F3, search for the Campfire operator and run it.
4. Scrub the timeline. The flames should move at once with no bake.
5. Render one frame in Cycles and one in EEVEE. There should be no black rectangles, and the ground glow should look alike.
6. Run the look test script, watch the clips and record the verdict in `docs/LOOK_TEST.md`.

**Before launch:**

1. Run `python tests/run_tests.py --release` for the release version.
2. Follow the walkthrough in `docs/RELEASE_CHECKLIST.md` on 4.5.

## Size

| T-Shirt Size | Estimated Hours | Notes |
| ------------ | --------------- | ----- |
| XL | 110 to 150 | Slice 1 is about 20 of those and may end the project. Hours for slices 2 to 10 depend on what the look test finds. |

## Considered And Rejected

Nothing here is built. Each entry names the alternative, then why it lost.

- **Viewport Transform node for Face Viewport.** Raises `Node must be run as tool` in a modifier on 5.1 and 5.2, and both manuals limit it to the Tool context.
- **Scene camera only, fading from other angles.** Removes the timer, but orbiting shows planes that don't face the view, which beginners would report as a bug. Also fails story 3.
- **Face Viewport as a Tool button.** Uses the node as intended, but isn't live, so planes go thin on orbit until clicked.
- **Viewport under the mouse wins.** Timers receive no mouse event. The most recently changed view identifies the same viewport during an orbit.
- **Capping effects at 7 planes and leaving scene settings alone.** Two fires lined up from the camera add to 14 planes and still show black, and 7 planes could weaken the look test.
- **Warning the buyer about the bounce limit.** A beginner's first Cycles render would be a black box until they read and acted on the warning.
- **Leaving planes visible to diffuse and glossy rays in Real mode.** Mean red brightness differed by 15% across engines (0.203 and 0.239), against about 1% with them hidden (0.2034 and 0.2057).
- **Python handler or driver for flicker.** A Noise F-curve modifier gave identical values on 5.1 and 5.2 with no code running.
- **Hard-coding the view target inside the node tree.** Copied scenes need their own target, and modifier inputs are per object.
- **Standalone script or hand-built `.blend` for the prototype.** Neither tests install or registration, and each leaves code or values to port. A 5.x file also can't be assumed to open correctly on 4.5.
- **Plumbing-only first slice.** Shows no fire, so the project's main risk would be tested later.
- **Look test with a real scene or outside opinions as required steps.** Each adds time or a dependency on other people to a gate that can recur. The owner can still do either.
- **A real beginner in the 4.5 gate.** The hard gate would depend on finding someone with 4.5 for every release, which is how boxes get skipped.
- **Shared library with AquaSuite.** Requires refactoring AquaSuite during its launch work, and ties two paid products to one dependency.
- **Writing everything fresh from the lessons.** Risks reintroducing bugs AquaSuite already fixed, and delays the first test run.
- **A new private repo once named, or choosing the name now.** The look test would wait on naming a product that may be cancelled.
- **Moving the add-on to the repo root.** Matches AquaSuite, but moves the PRD and removes the folder it was filed in.
- **Mode inside AquaSuite.** A product named for water would also do fire, and existing buyers might get it free.
- **Close-up hero fire.** Planes would likely show edges and repeating noise, which risks refunds.
- **Pre-rendered sprites.** Large downloads, fixed colours and timing, and a big art job up front.
- **Fixed or crossed planes.** The most likely to look flat as the camera moves.
- **Simulation Nodes or Mantaflow.** Both need a cache or bake before scrubbing, and Simulation Nodes are the hardest to test.
- **Rendering with whatever the switch says.** A forgotten switch could waste hours of rendering.
- **Modifier on the buyer's object.** Delete would have to clean up inside their object, the risky pattern from AquaSuite.
- **Eye checks on all three versions.** So many manual checks each release that they would likely get skipped.
- **12 presets.** 48 checks per release, and some effects need motion these planes may not do well.
- **Public code repo.** The source of a paid add-on would stay free to download, which undercuts sales.

## Revision History

| Date | Author | Summary of Change |
| ---- | ------ | ----------------- |
| 2026-11-01 | Blaxine | Initial plan. |
| 2026-11-01 | Blaxine | Slice 1 built. Later slices proceed before the look verdict on the owner's instruction; AC1 stays open until the owner records a verdict. Modifier inputs on 5.2 use modifier.properties.inputs. |
| 2026-11-01 | Blaxine | Slice 2 built: facing rule, view sync, steep fade and glow card. View sync passes in real windows on 5.1 and 5.2; 4.5 unproven, so S016 stays open. |
| 2026-11-01 | Blaxine | Slice 3 built: Real, Emissive and Both light modes. Real is about 6% apart across engines in the test scene. |
| 2026-11-01 | Blaxine | Slice 4 built: effect records, error pipeline, Delete, copied scenes and the tracked bounce limit. |
| 2026-11-01 | Blaxine | Slice 5 built: smoke on a point and smoke columns, carrying their own shading so they match between engines. |
| 2026-11-01 | Blaxine | Slice 6 built: fire on a mesh with no change to the source. Measured about 15 ms per frame at a million faces, so the limit is 2 million with a warning from 500,000. |
| 2026-11-01 | Blaxine | Slice 7 built: embers on legacy particles, following the timeline. |
| 2026-11-01 | Blaxine | Slice 8 built: panel with Simple and Advanced views, 8 presets with fixed stored numbers, sliders. Checked on a stand-in layout and in one real window on 5.2. |
