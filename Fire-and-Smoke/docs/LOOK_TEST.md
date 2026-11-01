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

## Speed

Target: the default Campfire runs at 24 fps in the EEVEE viewport, and costs no more than 3x an empty Cycles frame at 1080p, on this PC.

| Check | Blender | Result | Target | How |
| ----- | ------- | ------ | ------ | --- |
| Cycles against an empty frame, 1080p, 64 samples, denoised | 5.2.3 | 2.56x (13.79 s empty, 35.25 s with fire) | 3x or less | `tests/look_test.py --speed`, first render discarded |
| EEVEE viewport, 1574×888 in camera view | 5.2.3 | 59.8 fps | 24 fps or more | `tests/gui_viewport_speed.py` |
| EEVEE viewport, 1574×888 in camera view | 5.1.2 | 59.9 fps | 24 fps or more | `tests/gui_viewport_speed.py` |

The Campfire has 28 planes. The viewport numbers sit at the display's refresh cap, and the script redraws without accumulating samples, so the owner should confirm by playing the animation by hand. Blender 4.5 is not measured yet.

The target is unchanged, pending the owner's confirmation.

## Blender 4.5

Not installed yet, so nothing is measured on it. When it is, rerun the suite and both speed scripts, and note any differences here.
