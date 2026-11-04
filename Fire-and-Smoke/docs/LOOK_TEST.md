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

## Simulated Campfire (REQ-002)

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

## Blender 4.5

4.5.4 is installed now. The suite and every Simulated Campfire check above pass on it. The Campfire's own speed scripts haven't been rerun on it yet.
