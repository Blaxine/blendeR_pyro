# Release checklist

Internal: this file doesn't ship in the zip. This is a hard block with no exceptions. Nothing ships until every box here is ticked for the version named below, and `python tests/run_tests.py --release` refuses otherwise. AquaSuite's checklist said the same and 0.22.0 shipped with boxes open, so this one is enforced by the runner.

A box is ticked only when the check was done for this version, not when a test exists. Clear every box when starting a new version.

Version under test:

## Look and speed

- [ ] The look test has a recorded pass from the owner in `docs/LOOK_TEST.md`
- [ ] The default Campfire meets the confirmed speed target in the EEVEE viewport, by hand on this PC
- [ ] The default Campfire meets the confirmed speed target in Cycles: `tests/look_test.py --speed`
- [ ] The Simulated Campfire has the owner's Cycles verdict recorded in `docs/LOOK_TEST.md`
- [ ] The default Simulated Campfire's first play-through runs at 5 fps or more in a windowed EEVEE viewport, on this PC: `tests/gui_viewport_speed.py -- SIMULATED_CAMPFIRE`

## Blender 5.1 and 5.2 eye checks

Render every preset with `tests/render_presets.py`, and view each one in the viewport too. Each box means it looks right in that Blender and engine. The Simulated Campfire is held to the look bar in Cycles only: its EEVEE boxes mean it renders visible fire without errors. Play it from the first frame before viewing or rendering it.

### Blender 5.1

- [ ] Eye check: Candle, 5.1, Cycles
- [ ] Eye check: Torch, 5.1, Cycles
- [ ] Eye check: Campfire, 5.1, Cycles
- [ ] Eye check: Bonfire, 5.1, Cycles
- [ ] Eye check: Burning Object, 5.1, Cycles
- [ ] Eye check: Thin Smoke, 5.1, Cycles
- [ ] Eye check: Black Smoke Column, 5.1, Cycles
- [ ] Eye check: Embers, 5.1, Cycles
- [ ] Eye check: Simulated Campfire, 5.1, Cycles
- [ ] Eye check: Candle, 5.1, EEVEE
- [ ] Eye check: Torch, 5.1, EEVEE
- [ ] Eye check: Campfire, 5.1, EEVEE
- [ ] Eye check: Bonfire, 5.1, EEVEE
- [ ] Eye check: Burning Object, 5.1, EEVEE
- [ ] Eye check: Thin Smoke, 5.1, EEVEE
- [ ] Eye check: Black Smoke Column, 5.1, EEVEE
- [ ] Eye check: Embers, 5.1, EEVEE
- [ ] Eye check: Simulated Campfire, 5.1, EEVEE, renders visible fire

### Blender 5.2

- [ ] Eye check: Candle, 5.2, Cycles
- [ ] Eye check: Torch, 5.2, Cycles
- [ ] Eye check: Campfire, 5.2, Cycles
- [ ] Eye check: Bonfire, 5.2, Cycles
- [ ] Eye check: Burning Object, 5.2, Cycles
- [ ] Eye check: Thin Smoke, 5.2, Cycles
- [ ] Eye check: Black Smoke Column, 5.2, Cycles
- [ ] Eye check: Embers, 5.2, Cycles
- [ ] Eye check: Simulated Campfire, 5.2, Cycles
- [ ] Eye check: Candle, 5.2, EEVEE
- [ ] Eye check: Torch, 5.2, EEVEE
- [ ] Eye check: Campfire, 5.2, EEVEE
- [ ] Eye check: Bonfire, 5.2, EEVEE
- [ ] Eye check: Burning Object, 5.2, EEVEE
- [ ] Eye check: Thin Smoke, 5.2, EEVEE
- [ ] Eye check: Black Smoke Column, 5.2, EEVEE
- [ ] Eye check: Embers, 5.2, EEVEE
- [ ] Eye check: Simulated Campfire, 5.2, EEVEE, renders visible fire

## Blender 4.5

Eye checks on 4.5 are limited to these renders and the walkthrough.

- [ ] 4.5 render: Candle
- [ ] 4.5 render: Torch
- [ ] 4.5 render: Campfire
- [ ] 4.5 render: Bonfire
- [ ] 4.5 render: Burning Object
- [ ] 4.5 render: Thin Smoke
- [ ] 4.5 render: Black Smoke Column
- [ ] 4.5 render: Embers
- [ ] 4.5 render: Simulated Campfire, in EEVEE, renders visible fire

Follow this scripted beginner walkthrough on 4.5 from a clean profile:

1. Install the built zip.
2. Add a Campfire from the panel.
3. Orbit, then scrub the timeline.
4. Select a mesh and add Burning Object.
5. Render one frame.
6. Delete both effects with the bin icons.

- [ ] Beginner walkthrough done on 4.5, with no error popups and nothing left behind

## Every version

- [ ] `python tests/run_tests.py` passes with 4.5, 5.1 and 5.2 in the config
- [ ] `tests/gui_view_sync.py` passes in a window on 4.5, 5.1 and 5.2
- [ ] `tests/gui_viewport_visible.py` passes in SOLID and RENDERED, in a window on 4.5, 5.1 and 5.2
- [ ] `tests/gui_undo.py` passes every sequence in a window on 4.5, 5.1 and 5.2
- [ ] `tests/gui_viewport_speed.py` run on 4.5, 5.1 and 5.2, with results in `docs/LOOK_TEST.md`
- [ ] The built zip is installed from disk and tested in a clean profile on 4.5
- [ ] The built zip is installed from disk and tested in a clean profile on 5.1
- [ ] The built zip is installed from disk and tested in a clean profile on 5.2
- [ ] Installing the built zip over a turned-off older version loads the new code, in a real window

## Before the store page

- [ ] The name is final in `constants.py` and `blender_manifest.toml`, and the id and prefix are final
- [ ] The public issues repo exists, and `SUPPORT_URL` and the manifest `website` point at it
- [ ] The private code repo is private: GitHub's API returns 404 without a login
- [ ] The store text in `docs/STORE_PAGE.md` has no placeholders and states every limit
- [ ] The version in `blender_manifest.toml` is the version being released
