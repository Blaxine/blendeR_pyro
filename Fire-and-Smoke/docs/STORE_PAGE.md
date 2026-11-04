# Store page text

Draft for the owner. `NAME` and `PRICE` are placeholders until they're decided (Q1, Q2). Internal: this file doesn't ship in the zip.

---

## NAME: fire and smoke with no baking

Add believable fire and smoke to your Blender scene in one click. Pick a preset, press play, and scrub your timeline straight away, with no bake to wait for.

**9 presets:** Candle, Torch, Campfire, Simulated Fire, Bonfire, Burning Object, Thin Smoke, Black Smoke Column and Embers.

- **No baking for flames and smoke.** They play and scrub instantly.
- **Stays convincing as your camera moves.** Planes keep facing the camera, and fade to a soft glow from steep angles.
- **Fire that lights your scene,** with a flickering light that looks the same in Cycles and EEVEE.
- **Set your own mesh on fire.** Your object isn't changed.
- **A real simulated fire too,** with volumetric flames and smoke, and still no bake step: it simulates as you play. Start it as a **Normal Fire**, a **Candle Fire** or a **Campfire**, and switch between them later. The Campfire burns from several logs, with flickering tongues shading from a pale core to red tips.
- **Wind** that bends the Simulated Fire and carries the embers, with Power, Gusts and Direction.
- **Cleaning up is safe.** Delete removes only what the add-on made, even in copied scenes.
- **A simple panel** with plain messages when something can't be done.

## What it's made for, and what it isn't

We'd rather you know before you buy:

- **Works for mid-ground shots.** Extreme close-ups aren't supported. Every preset but the Simulated Fire is planes with animated noise, not a simulation.
- **The Simulated Fire plays from the first frame.** It simulates as the timeline plays forward: jumping ahead holds the last simulated frame, and a render of a frame it hasn't reached shows no fire. Going back to the first frame and playing recovers it.
- **The Simulated Fire is made for Cycles.** EEVEE renders it with a weaker look.
- **The Simulated Fire uses disk space.** About 140 MB for a 250-frame Campfire at the default Detail, more at higher Detail. It's kept in a `fas_cache` folder beside your saved .blend, and removed when you delete the effect.
- **Top-down shots look weak.** From high above, flames fade to a soft glow.
- **Embers replay from the start when scrubbed.** "No baking" means instant scrubbing for flames and smoke, not embers or the Simulated Fire.
- **Cycles and EEVEE match with the default light.** Emissive lighting is Cycles-focused.
- **Plane flames and smoke appear to rise, but nothing travels through your scene.** They don't react to objects or wind. The Simulated Fire and embers do react to wind.

## Requirements

Blender 4.5, 5.1 or 5.2. Works in Cycles and EEVEE.

## Price

PRICE

## License

GPL-3.0-or-later, as Blender add-ons are.

## Support

SUPPORT LINK: add only after the public issues repo exists.
