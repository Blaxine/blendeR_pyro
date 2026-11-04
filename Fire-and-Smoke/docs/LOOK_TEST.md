# Look test record

The Campfire has to look like fire, by eye, in both engines. That verdict belongs to the owner.

## Verdict

**Round 1: pending the owner's verdict.**

| Date | Round | Verdict | Who | Notes |
| ---- | ----- | ------- | --- | ----- |
|  | 1 |  | Owner |  |

Later slices were built before this verdict, on the owner's instruction of 2026-11-01. If the Campfire fails twice, the project still stops, whatever else has been built.

## How to run it

The scene is built by `tests/look_test.py`: dark ground, dusk sky, Campfire at the origin, and a 50 mm camera about 9 m away orbiting 70 degrees over 96 frames. Colour management stays at factory settings.

```bash
blender -b --factory-startup --python tests/look_test.py -- --out look_test_output
```

Clips land in `look_test_output/`, which git ignores. Add `--stills` for contact sheets of frames 12 to 72.

Clips ready for the verdict, rendered on 5.2.3 from the finished add-on:

- `look_test_output/5.2_CAMPFIRE_CYCLES_0001-0096.mp4`
- `look_test_output/5.2_CAMPFIRE_EEVEE_0001-0096.mp4`

Every preset is rendered in both engines on 5.1 and 5.2 in `look_test_output/presets/`, with a contact sheet per version and engine. To re-create them, run `tests/render_presets.py`.

## Decisions waiting on the owner's eye

- **Smoke shading:** smoke carries its own shading, using the Blended render method, and matches between engines (mean pixel difference 0.001 to 0.004). It doesn't pick up scene lights or a nearby fire's colour.
- **Ground line:** flames fade out at their base, which hides the line where planes meet the ground. Mesh fires stand clear of the mesh towards the viewer, which removes the hard cuts.
- **Weakest looks so far:** the Black Smoke Column stays fairly even in width instead of widening, and Burning Object reads as separate flame shapes on a box.

## Speed

Target: the default Campfire runs at 24 fps in the EEVEE viewport, and costs no more than 3x an empty Cycles frame at 1080p, on this PC.

| Check | Blender | Result | Target | How |
| ----- | ------- | ------ | ------ | --- |
| Cycles against an empty frame, 1080p, 64 samples, denoised | 5.2.3 | 2.63x (11.95 s empty, 31.42 s with fire) | 3x or less | `tests/look_test.py --speed`, first render discarded |
| Cycles against an empty frame, 1080p, 64 samples, denoised | 5.1.2 | 2.71x (11.55 s empty, 31.29 s with fire) | 3x or less | `tests/look_test.py --speed`, first render discarded |
| EEVEE viewport, 1574×888 in camera view | 5.2.3 | 59.9 fps | 24 fps or more | `tests/gui_viewport_speed.py` |
| EEVEE viewport, 1574×888 in camera view | 5.1.2 | 59.9 fps | 24 fps or more | `tests/gui_viewport_speed.py` |

Measured on the finished add-on. The Campfire has 28 flame planes and a glow card. The viewport numbers sit at the display's refresh cap, and the script redraws without accumulating samples, so the owner should confirm by playing the animation by hand. Blender 4.5 is not measured yet.

The target is unchanged, pending the owner's confirmation.

## Simulated Fire as a Campfire (REQ-002)

A real Mantaflow fire, held to the look bar in Cycles. In EEVEE it only has to render visible fire.

REQ-002's first step waits on round 1 of the Campfire look test above, which is still pending. The preset was built before that verdict on the owner's instruction of 2026-11-04 to implement every slice, as REQ-001's later slices were. The Campfire's kill rule still decides the project.

### Verdict in Cycles

**Pending the owner's verdict.**

| Date | Verdict | Who | Notes |
| ---- | ------- | --- | ----- |
|  |  | Owner |  |

To render it, play from the first frame and render one frame per engine:

```bash
blender -b --factory-startup --python tests/render_presets.py -- --only SIMULATED_CAMPFIRE --frame 90
```

`--frame` steps one frame at a time from frame 1 to that frame before rendering, since Replay only simulates forward.

### Values proposed for the verdict

Tuned by render on 5.2.2 from Quick Smoke's starting values. With those, the whole plume glowed orange in the fire light and the flame was a smooth, white-hot column. These answer REQ-002's Q16 once the owner passes them.

| Setting | Quick Smoke start | Proposed |
| ------- | ----------------- | -------- |
| Emitter | 0.35 m disc at 0.05 m, Smoke & Fire, Inflow, surface distance 1.0 | unchanged |
| Domain | 1.4 × 1.4 × 2.6 m, centred 1.25 m up, CFL 4.0, 64 divisions | unchanged |
| Vorticity | 0 | 0.2 |
| Burning rate | 0.75 | 1.1 |
| Volume density | 5 | 3 |
| Volume colour (smoke) | 0.5 grey | 0.05 grey |
| Blackbody intensity | 1 | 1 |
| Fire light | 90 W (the Campfire's) | 45 W, 0.3 m radius, 0.5 m up |

Blackbody intensity stays at 1: at 0.6 the flames looked as good in Real, but lit the ground only 6% above an unlit render in Emissive, against 10% at 1.

### Speed

Target (AC3): the default's first play-through runs at 5 fps or more in a windowed EEVEE viewport on this PC. `tests/gui_viewport_speed.py -- SIMULATED_CAMPFIRE` times frames 1 to 96 in Rendered camera view: the first pass simulates every frame, the second reads the cache.

| Blender | Detail | First play-through | From the cache | Viewport | Target |
| ------- | ------ | ------------------ | -------------- | -------- | ------ |
| 5.2.2 | 64 (default) | 13.7 fps | 59.1 fps | 1574×888 | met |
| 4.5.4 | 64 (default) | 14.0 fps | 61.7 fps | 1585×886 | met |
| 5.2.2 | 96 | 4.6 fps | 49.2 fps | 1574×888 | the slider's soft maximum |
| 5.2.2 | 128 | 2.4 fps | 33.3 fps | 1574×888 | |
| 5.1 | | not measured | | | not installed on this PC |

The 96 and 128 rows were measured before vorticity was added. The script redraws without accumulating samples, so the owner should confirm by playing by hand.

### What a render past the simulated frames shows

On 4.5.4 and 5.2.2, after simulating frames 1 to 30 and jumping to frame 50, the viewport holds frame 30's fire but a Cycles render of frame 50 shows no fire at all (REQ-002's Q14). The buyer docs say to play to a frame before rendering it.

### Engines

EEVEE renders visible fire with no error on 4.5.4 and 5.2.2 (`tests/test_sim_fire.py`), and the Simulated Campfire draws in the viewport in Solid and Rendered on both (`tests/gui_viewport_visible.py`). In the 5.2.2 renders at frames 40 and 90 it reads close to Cycles, a little softer. The panel and store page still promise only a weaker look in EEVEE, since the Cycles look is the one held to the bar. 5.1 isn't installed on this PC.

### Undo

`tests/gui_undo.py -- sim` (create, play, delete, undo, play, undo, redo, play) passes in a window on 4.5.4 and 5.2.2, as do the `embers` and `plain` sequences.

## Simulated Fire presets (REQ-003)

The Simulated Fire has three presets, as AquaSuite's liquids do: Normal Fire, Candle Fire and Campfire. The Campfire started as the values above, and was then made to burn like a real campfire (see below). The other two were tuned by render in Cycles on 5.2.2 on 2026-11-04, from the Campfire's values, and are proposed for the owner's verdict.

### Verdict in Cycles

**Pending the owner's verdict, for each preset.**

| Date | Preset | Verdict | Who | Notes |
| ---- | ------ | ------- | --- | ----- |
|  | Normal Fire |  | Owner |  |
|  | Candle Fire |  | Owner |  |

To render all three in both engines:

```bash
blender -b --factory-startup --python tests/render_presets.py -- --only SIMULATED_CAMPFIRE --frame 90
```

Add `--sim CANDLE_FIRE` to render one of them.

### Values proposed for the verdict

| Setting | Normal Fire | Candle Fire | Campfire |
| ------- | ----------- | ----------- | -------- |
| Emitter | 0.2 m disc at 0.03 m, Smoke & Fire | 5 mm disc at 5 mm, Fire only | 8 log patches, 6 to 11 cm across, 2 to 10 cm up, reaching 0.39 m, Smoke & Fire |
| Domain | 0.9 × 0.9 × 1.8 m, centred 0.85 m up | 6 × 6 × 16 cm, centred 7.5 cm up | 1.4 × 1.4 × 2.6 m, centred 1.25 m up |
| Detail | 64 (grid 32 × 32 × 64) | 96 (grid 36 × 36 × 96) | 64 (grid 34 × 34 × 64) |
| Vorticity | 0.3 | 0 | 0.5 |
| Flame vorticity | 0.5 | 0.5 | 1.5 |
| Burning rate | 1.3 | 4.0 | 0.9 |
| Heat buoyancy (beta) | 0.6 | 0.1 | 1.0 |
| Flame maximum temperature | 3.5 | 6.0 | 3.0 |
| Smoke from flames | 1.0 | 0 | 1.0 |
| Volume density | 2 | 1 | 3 |
| Volume colour (smoke) | 0.15 grey | 0.05 grey | 0.05 grey |
| Blackbody intensity | 1.5 | 25 | 0 |
| Flame colour | none | none | ramp at strength 7 |
| Fire light | 20 W, 0.2 m radius, 0.3 m up, flicker 0.25 | 0.5 W, 0.02 m radius, 3 cm up, flicker 0.12 at speed 5 | 45 W, 0.3 m radius, 0.5 m up, flicker 0.3 |

How they were found:

- **Normal Fire.** With the Campfire's buoyancy, a 0.2 m emitter made a smooth, tall column, glowing orange all the way up. With heat buoyancy at 0.6 and a burning rate of 1.3, the flame burns out at about knee height and grey smoke rises above it.
- **Candle Fire.** At full heat buoyancy a 1 cm flame burned the whole height of a 25 cm domain, two or three cells wide. With a 16 cm domain, heat buoyancy at 0.1 and a burning rate of 4, the flame is about 4 cm tall. A flame that thin rendered dull orange at blackbody 1: at 25, with a maximum temperature of 6, it's white at the base and orange at the tip. It still shows faint banding up the flame, which the owner should judge.

### Speed

`tests/gui_viewport_speed.py -- SIMULATED_CAMPFIRE <preset>`, frames 1 to 96 in a windowed EEVEE viewport in Rendered camera view. The target (AC3) is 5 fps on the first play-through.

| Blender | Preset | First play-through | From the cache | Viewport | Target |
| ------- | ------ | ------------------ | -------------- | -------- | ------ |
| 5.2.2 | Normal Fire | 14.2 fps | 61.9 fps | 1574×888 | met |
| 5.2.2 | Candle Fire | 6.7 fps | 62.1 fps | 1574×888 | met |
| 5.2.2 | Campfire (logs) | 12.2 fps | 60.3 fps | 1574×888 | met |
| 4.5.4 | Normal Fire | 14.7 fps | 62.1 fps | 1585×886 | met |
| 4.5.4 | Candle Fire | 6.9 fps | 61.8 fps | 1585×886 | met |
| 4.5.4 | Campfire (logs) | 9.8 fps | 61.9 fps | 1585×886 | met |
| 5.1 | | not measured | | | not installed on this PC |

The Candle Fire is the slowest: its 96 divisions over a small domain make more cells than the Campfire's 64.

### Engines

All three render visible fire in Cycles and EEVEE on 5.2.2 at frame 90 (`tests/render_presets.py`), and burn on 4.5.4 and 5.2.2 (`tests/test_sim_presets.py`).

### Viewport shading

Found on 2026-11-04, after the owner couldn't see the fire. Blender's **Material Preview** draws no fluid simulation, on 4.5.4 and 5.2.2. It showed only the domain's wireframe and the emitter, even after 30 seconds, and a Quick Smoke fire beside it didn't show either. **Solid** and **Rendered** both show the fire. The panel says so in the fire's box, and warns in Material Preview.

`tests/gui_viewport_visible.py` used to pass the Simulated Campfire in every mode, because the wireframe box alone changed about 4,000 pixels. It now counts only fire-coloured pixels for it, and reports Material Preview as known.

In the owner's own startup scene, the fire was also inside the default cube, which sits at the 3D cursor. Create now names any mesh of the buyer's that hides a fire (`core/covering.py`), and the fire's box says so too.

## A real campfire, and wind (2026-11-04)

The owner asked for the Campfire to look like a real one: erratic, with flames that come and go, and the orange colouring of a real fire. Tuned by render in Cycles on 5.2.2, frames 80, 86 and 92, against the values above.

**Pending the owner's verdict.**

What made the difference:

- **Logs, not a disc.** One disc burned as one smooth, rounded column. Eight small patches at different heights, like the tops of logs, burn as separate tongues that merge, split and lean (`CAMPFIRE_LOGS` in `effects/sim_presets.py`).
- **More swirl in the flames.** Flame vorticity 1.5 (Blender's default is 0.5) and vorticity 0.5 tear the tongues into licks. A slower burning rate, 0.9, lets them reach a little higher before they go out.
- **A flame colour ramp.** Blackbody alone shaded the whole flame one orange. The Campfire's volume now takes its emission colour from the flame through a ramp: dark red at the thin edges, deep orange, orange, and a pale yellow core where it burns hottest (`FLAME_RAMP` in `effects/sim_fire.py`). The flame's strength times 7 is the emission strength, and blackbody is off. Normal Fire and Candle Fire keep their blackbody look.
- **What didn't work.** Mantaflow's noise upscaling gave fine detail, but simulated 2.6 times slower, well under the 5 fps target. A noise texture on the emitter starved the flames into a few faint wisps.

Headless, the Campfire simulates as fast as before: about 4.6 s for 60 frames. In a windowed viewport its first play-through is 12.2 fps on 5.2.2 (15.1 fps from one disc) and 9.8 fps on 4.5.4, above the 5 fps target.

### Wind

The **Wind** button in the Add panel makes an owned Wind force field, a Plane field 3 m upwind of the 3D cursor and 1 m up, facing the way it blows. Its box has **Power**, **Gusts** and **Direction**.

- Blender's wind strength 1 lays a campfire flat and pushes its flames into the side of its box. **Power 1 is strength 0.25**, a strong breeze, so the slider's useful range is 0 to 1. It goes up to 4 for a gale. It starts at 0.4.
- **Gusts 1 is the field's noise at 2.** It starts at 0.3.
- After 40 frames at Power 1, the Campfire's plume moved from 0.49 to 0.68 of the way across its domain on 5.2.2, and from 0.44 to 0.58 on 4.5.4 (`tests/test_wind.py`).
- Wind is not a setting the Replay cache notices, so adding, changing or deleting a wind clears every Simulated Fire's cache. The buyer plays from the first frame again to see it.
- The plane fires and smoke are animated noise, so wind doesn't move them. The box says so.

## Blender 4.5

4.5.4 is installed now. The suite and every Simulated Campfire check above pass on it. The Campfire's own speed scripts haven't been rerun on it yet.
