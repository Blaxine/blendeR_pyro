# REQ-001-PRD — Fire and Smoke Add-on

| Field | Value |
| ----- | ----- |
| ID | REQ-001-PRD |
| Title | Fire and Smoke Add-on |
| Status | Todo |
| Author | Blaxine |
| Created | 2026-11-01 |
| Last Updated | 2026-11-01 |

## Problem Statement

Blender beginners want believable fire and smoke in their scenes, usually in the middle distance of a shot with a moving camera. The ways they can get it today ask too much of them. Baking makes them wait before they can see their timing, ready-made sprites are large downloads with fixed colours and timing, and flat planes give themselves away as soon as the camera moves.

AquaSuite already serves these beginners for water, but nothing in it covers fire, and a product named for water is the wrong home for it.

## Solution

A new paid Blender add-on, sold separately from AquaSuite to the same beginners. They pick one of 8 presets, such as a candle, campfire or smoke column, and get fire or smoke that plays back and scrubs instantly without baking, keeps its shape as the camera moves, and lights the scene around it. It works in Cycles and EEVEE on Blender 4.5, 5.1 and 5.2.

The product depends on the look. A single campfire is judged by eye in both engines before anything else is built. If it doesn't look like fire, even after one round of adjustment, the project stops.

The product only promises what it has been checked to do. It doesn't ship until every promised Blender version and engine has passed its checks, with no exceptions. The store page states its limits openly: it's made for mid-ground shots, extreme close-ups aren't supported, top-down shots look weak, and embers replay from the start when scrubbed.

## User Stories

1. As a Blender beginner, I want to add fire, smoke, a smoke column or embers from a preset in a simple panel that tells me clearly when something can't be done, so that I get a believable effect without learning how it's made
2. As a Blender beginner, I want to set one of my own meshes on fire without my object being changed, so that I can burn something in my scene and still keep the original intact
3. As a Blender beginner, I want flames and smoke to scrub instantly and keep facing me as I move around the viewport, with final renders always facing the scene camera, so that I can work on my shot without waiting and a forgotten preview setting can't waste a render
4. As a Blender beginner, I want my fire to cast flickering light that looks the same in Cycles and EEVEE, so that it feels part of the scene whichever engine I use
5. As a Blender beginner, I want deleting an effect to remove only what the add-on made for that effect, even in copied scenes or after I've changed things myself, so that cleaning up never destroys my work

## Out of Scope

- Extreme close-ups or hero shots of fire. Top-down shots are also not a supported look: they're expected to look weak.
- Real simulated motion. Flames and smoke appear to rise, but nothing actually travels through the scene.
- A "no baking" promise for the whole add-on. It covers flames and smoke; embers replay from the start when scrubbed.
- A matching look between engines for emissive lighting. The Cycles and EEVEE match covers the default light only, and emissive lighting is Cycles-focused.
- A fire or smoke mode inside AquaSuite, or a free version for existing AquaSuite buyers.
- More than 8 presets in the first release.
- Blender versions other than 4.5, 5.1 and 5.2.
