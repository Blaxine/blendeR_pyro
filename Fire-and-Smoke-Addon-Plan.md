# Fire and Smoke add-on: resolved plan

Written on 2026-11-01 from a grill-me interview. The add-on doesn't have a name yet. No code exists.

## What's being built

A new paid Blender add-on, sold separately from AquaSuite to the same beginners. It makes fire and smoke from camera-facing planes with animated procedural noise, built with Geometry Nodes, so flames and smoke scrub instantly with no baking. It's meant for mid-ground shots with a moving camera, in both Cycles and EEVEE, on Blender 4.5, 5.1 and 5.2.

The first release has fire and smoke on a point, fire on a buyer's mesh, smoke columns, and embers, across 8 presets.

**The first job is a single Campfire prototype, with no panel or presets.** If it doesn't look like fire, nothing else gets built.

## Decisions

| Area | Decision | What it costs or rules out |
| ---- | -------- | -------------------------- |
| Product | Separate paid add-on for beginners | Needs its own repo, store page, support and release checks |
| Hardest shot | Mid-ground with a free camera | Extreme close-ups aren't supported |
| Look | Procedural noise only, no image files | Pure noise can look like a soft blob; see the look test below |
| Flames and smoke | Geometry Nodes stack of planes with offset noise | Nothing really travels: rising motion is noise scrolling upward |
| Embers and sparks | Legacy particle system | A second system; embers replay from the start when scrubbed |
| Plane direction | Spin around the vertical axis only; fade to a low glow from steep angles | Top-down shots look weak |
| Viewport preview | A switch: Face Viewport or Face Camera | Must be labelled as preview-only |
| Final renders | Always face the scene camera, whatever the switch says | Viewport renders still need a rule |
| Fire on a mesh | A separate object that reads the mesh and follows it; the buyer's object is never changed | Dense meshes may be slow; a deleted source needs handling |
| Fire's light | Real flickering light, emissive planes, or both, chosen per effect; real light is the default | One more owned object to manage; mesh fires need a sensible light position |
| Engines | Cycles and EEVEE must match | The promise covers the default light only; the panel notes that emissive lighting is Cycles-focused |
| Blender versions | 4.5, 5.1 and 5.2, with the focus on 5.1 and 5.2 | 4.5 and 5.2 must be installed on this PC |
| Presets | 8 | 32 eye checks per release |
| Speed target | Default Campfire: 24 fps in the EEVEE viewport, and no more than 3x the cost of an empty Cycles frame at 1080p, measured on this PC | The numbers are provisional until the prototype is measured |
| Code and support | Private code repo from the first commit; public issues-only repo created before any link ships | The owner creates both repos |

**Example presets (the list isn't final):** Candle, Torch, Campfire, Bonfire, Burning Object, Thin Smoke, Black Smoke Column, Embers.

## The look test

1. Build one Campfire, with no panel or presets, and judge it by eye in both engines.
2. If it fails, a few grayscale shape masks may be added, then test again. This drops the "no images" rule and adds art and licensing work.
3. If it fails again, stop the project.

Measure the speed target during this test and confirm or change the numbers.

## Release gate

This is a hard block with no exceptions. AquaSuite's checklist said nothing ships until every box is ticked, and 0.22.0 shipped with boxes still open. Don't repeat that here.

- **Blender 5.1 and 5.2:** the owner views and renders all 8 presets in both engines.
- **Blender 4.5:** automated tests, one render per preset, and a beginner session.
- **All versions:** automated tests pass, and the built zip is installed and tested itself.
- **Speed:** the default Campfire meets the confirmed target.

## What the store page must say

- Works for mid-ground shots. Extreme close-ups aren't supported, and top-down shots look weak.
- Flames and smoke need no baking and scrub instantly. Embers replay from the start, so don't claim "no baking" for the whole add-on.
- Cycles and EEVEE match with the default light. Emissive lighting is Cycles-focused.
- Supported versions are Blender 4.5, 5.1 and 5.2.

## What carries over from AquaSuite

| Lesson | How it applies here |
| ------ | ------------------- |
| Installing over a turned-off version loaded stale code (the `FLOAT_MATERIALS` error) | Clear the add-on's modules at the top of `__init__.py` from the first version, with an upgrade test |
| Delete in a copied scene removed the original's objects | Delete only inside this scene's own setup; give copied setups a new ID; test this from the start |
| Emitters stopped at the old timeline end | Embers follow timeline changes, using the same range handling |
| Deleting the lighting replaced a world the user chose later | Restore or remove something only if it's still the add-on's own, and apply this to the fire light |
| Saved preset choices are stored by position | Add new presets to the end of the list and sort the display order separately |
| Operator settings stayed set between uses | Use `SKIP_SAVE` on preset choices and delete options |
| Testing without a window can't confirm everything | Test panels with a stand-in layout, but anything visual goes on the eye-check list |
| Install tests could touch real add-ons | Point `BLENDER_USER_RESOURCES` at a temp folder for every install test |
| The support link pointed at a repo meant to go private | Create the public issues repo before writing any link into the add-on |
| The stated minimum version was never tested here | Install every promised Blender version before making the promise |
| AquaSuite's look was only partly checked in EEVEE | Both engines are in the gate from the start |
| Simple and Advanced views helped beginners | Use the same panel approach, with hints and a clear message when something can't be done |

## Build order

1. Install Blender 4.5 and 5.2. Create the private code repo.
2. Run the Campfire look test.
3. Add the camera rule, the preview switch and the light options.
4. Add creation, delete, ownership and copied-scene handling, with tests.
5. Add fire on a mesh and smoke columns.
6. Add embers.
7. Build the panel and all 8 presets.
8. Create the public issues repo, then add support links.
9. Run the release gate, then launch.

## Still to decide

| Open item | Decide when |
| --------- | ----------- |
| Add-on name | Before creating the repos |
| Price | After the look test passes |
| Exact preset list | When presets are built; each must pass the eye check |
| Whether smoke reacts to scene lights or carries its own shading | During the look test; it must match in both engines |
| How to hide the hard line where planes cut through the ground or a mesh | During the look test; if it can't be hidden, add it to the store page limits |
| Whether Face Viewport can work on 4.5 | Prove it before building the switch; if it can't work there, decide whether 4.5 goes without it or the promise changes |
| What viewport renders and previews face | When the switch is built |
| What to do when a scene has no camera | When the camera rule is built; the panel must say what's wrong |
| Light position for mesh fires | When fire on a mesh is built |
| Limit for dense or deforming meshes, and what happens if the source is deleted | When fire on a mesh is built, using real measurements |
| Whether embers stay on legacy particles | If a supported Blender release deprecates them |

## Options that lost

- **Mode inside AquaSuite:** a product named for water would also do fire, and existing buyers might get it free.
- **Close-up hero fire:** planes would likely show their edges and repeating noise, which risks refunds.
- **Pre-rendered sprites:** large downloads, fixed colours and timing, and a big art job up front.
- **Fixed or crossed planes:** the most likely to look flat as the camera moves.
- **Simulation Nodes:** needs a cache to scrub, and it's the hardest to test.
- **Scene camera only:** orbiting the viewport shows thin slices, which beginners would report as a bug.
- **Render with whatever the switch says:** a forgotten switch could waste hours of rendering.
- **Modifier on the buyer's object:** Delete would have to clean up inside their object, the risky pattern from AquaSuite.
- **Eye check on all three versions:** so many manual checks each release that they would likely get skipped.
- **12 presets:** 48 checks per release, and some effects need motion these planes may not do well.
- **Public code repo:** the source of a paid add-on would stay free to download, which undercuts sales.
