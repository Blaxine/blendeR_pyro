# Fire and Smoke: a Blender add-on

A paid Blender extension for beginners (id `fire_and_smoke`, GPL-3.0-or-later). It makes fire, smoke, smoke columns and embers from presets, built from camera-facing Geometry Nodes planes with animated noise, so they scrub with no baking. It also has a **Simulated Fire**, a real Mantaflow fire with Normal Fire, Candle Fire and Campfire presets, and a **Wind** effect. It targets Blender 4.5, 5.1 and 5.2. Only 4.5.4 and 5.2.2 are installed on this PC.

The owner is Blaxine. They're not a programmer: they ask for features in plain words, sometimes with typos, and judge them by eye in Blender.

## Layout

The git root is `blendeR_pyro/`. The add-on itself is `Fire-and-Smoke/`:

| Folder | What's in it |
| ------ | ------------ |
| `__init__.py`, `constants.py`, `blender_manifest.toml` | Registration (`_MODULES`), kinds and labels, version |
| `core/` | Registry (`scene.fas_effects` and every slider's update), ownership tags, delete, error guards, handlers, cache folder |
| `effects/` | One module per effect: `campfire`, `smoke`, `mesh_fire`, `embers`, `sim_fire`, `sim_presets`, `wind`, plus shared builders |
| `ui/` | `panel.py` (sidebar panel) and `control_spec.py` (which controls each kind's box shows) |
| `tests/` | The suite (`test_*.py`), GUI scripts (`gui_*.py`), render scripts |
| `docs/` | README for buyers, TROUBLESHOOTING, STORE_PAGE, LOOK_TEST (internal), RELEASE_CHECKLIST (internal) |
| `reqs/` | Requirement docs (`todo/`, `in-progress/`) and `GLOSSARY.md` |
| `dist/` | The built installer zip |

## Running things

Use the full paths. Blender isn't on PATH.

- **The suite, in every installed Blender:** `"C:/Program Files/Blender Foundation/Blender 5.2/5.2/python/bin/python.exe" tests/run_tests.py`, from `Fire-and-Smoke/`. It takes about 3 minutes, so run it in the background. `-k name` runs only the test files whose names contain `name`. `--release` adds the release gate. Blenders are listed in `tests/blender_paths.local.json` (git-ignored).
- **A test file** is a list of `test_*` functions that call `lib.check(name, ok, detail)` and `lib.info(...)` from `fas_testlib`, ending with `lib.main(globals())`. Tests in a file run in order and share state through a module `STATE` dict.
- **Windowed speed:** `blender --factory-startup --python tests/gui_viewport_speed.py -- SIMULATED_CAMPFIRE CAMPFIRE`. The target is 5 fps on the first play-through.
- **Renders for the owner's verdict:** `blender -b --factory-startup --python tests/render_presets.py -- --only SIMULATED_CAMPFIRE --frame 90`, with `--sim NORMAL_FIRE` for another preset.
- **Build the installer:** remove the old zip from `dist/`, then run `blender --factory-startup --command extension build --source-dir . --output-dir dist`, from `Fire-and-Smoke/`. The manifest's `paths_exclude_pattern` keeps tests, reqs and internal docs out.

## Conventions

- **Every effect is owned.** Everything Create builds is tagged with `naming.tag(id_block, kind, uuid)` and sits in the effect's own collection. It's recorded as an entry in `scene.fas_effects`. Delete removes only tagged data. Never change or delete the buyer's own objects.
- **A new effect kind** needs:
  - a `KIND_*` constant and a label in `constants.py`
  - its module in `__init__._MODULES`
  - its controls in **both** `SIMPLE` and `ADVANCED` in `control_spec.py`, since a test checks every kind
  - a button in the Add panel
  - `@delete.guarded_create` on its Create operator
- **Sliders** are properties on `FAS_EffectEntry` in `core/registry.py`, each with an update wrapped in `@errors.guard_update(...)`. Most are multipliers, default 1, that scale a `base_*` value the preset set.
- **The Simulated Fire's sliders fall into two groups:**
  - **Simulation settings** go through `_simulation_change`, which clears the Replay cache: Detail, Flame Intensity, Flame Noise, Smoke Amount and Wind. The buyer must play from the first frame to see a change.
  - **Material settings** go through `sim_fire.set_look` and show straight away: Flame Colour, Emission Strength, Temperature, Density and Smoke Colour.
- **Simulation presets** (`effects/sim_presets.py`):
  - A preset is plain data, written once by `apply`.
  - A new slider must be added to `SNAPSHOT_ENTRY`, reset in `apply`, and scale a `base_*` that `apply` sets.
  - A fire saved before the slider existed must keep its look: adopt the current value as the base when the base key is missing from `entry.keys()`.
- **Blender 4.5 and 5.2 must both pass.** Compare floats with a tolerance, because properties are float32.

## Things that bit before

- **Material Preview draws no fluid simulation**, Quick Smoke included. Use Rendered or Solid to see the Simulated Fire.
- **The default cube hides a fire made at the 3D cursor.**
- **Clearing the Replay cache:** reassign `settings.cache_type = settings.cache_type`. That's `sim_fire.clear_cache`.
- **A new object has no force field:** `obj.field` is None until `bpy.ops.object.forcefield_toggle()` runs under `context.temp_override(...)`. Blender's wind strength 1 lays a campfire flat, so Power 1 is strength 0.25.
- **Blender caps `flame_vorticity` at 2**, and vorticity at 4.
- **Mantaflow noise upres is too slow** (2.6 times slower), and **a flow texture starves the flames**. Realism came from the emitter's shape, swirl and a flame colour ramp instead.
- **Test renders:**
  - Write an EXR and read linear pixels: tone mapping clips a bright flame.
  - Use a black world, so the sky doesn't swamp the fire.
  - Give render paths as absolute paths. A relative `//` path lands at `C:\`.
- **Noise upres writes `waveletNoiseTile.bin`** into the working folder. Delete it.

## Safety with the owner's Blender

- **Never kill Blender.** No `taskkill`: the owner may have unsaved work open.
- **GUI scripts must not touch saved preferences.** Set `bpy.context.preferences.use_preferences_save = False` first, and always use `--factory-startup`.
- **`addon_utils.enable(...)` loads the owner's installed copy**, not this working copy. To see the working copy in a GUI script, import `tests/fas_testlib.py`, as the tests do.

## Working style

- **Edit scripts:** for multi-line edits, write a small Python script to the scratchpad that asserts each old string occurs once, then run it with Blender's bundled Python. Bash heredocs that contain apostrophes break.
- **Look changes are judged by render.** Render in Cycles on 5.2 with a small probe script in the scratchpad (a dark ground and sky, 320×400, 32 samples, a few frames side by side), look at the result, and say what you saw. `tests/render_presets.py` is the full version. Record the values and findings in `docs/LOOK_TEST.md`. The owner's verdict is theirs to give: mark it pending.
- **Every feature updates the docs:**
  - `README.md` (Good to know)
  - `docs/TROUBLESHOOTING.md` when there's a new way for it to go wrong
  - `docs/STORE_PAGE.md`
  - `reqs/GLOSSARY.md`
  - the current REQ's notes and Revision History
  - `docs/LOOK_TEST.md` for anything tuned by eye
- **Writing for buyers:** plain words, short sentences, bold lead-ins, and no jargon a beginner wouldn't know.
- **After a feature:**
  1. Run the suite on both Blenders.
  2. Commit on the current branch, ending the message with the attribution line.
  3. Rebuild the zip.
  4. Tell the owner to reinstall it.
