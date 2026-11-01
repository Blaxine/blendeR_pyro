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

## Blender 4.5

Not installed yet, so nothing is measured on it. When it is, rerun the suite and both speed scripts, and note any differences here.
