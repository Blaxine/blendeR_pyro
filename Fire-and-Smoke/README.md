# Fire and Smoke

Add fire, smoke, smoke columns and embers to a Blender scene from presets. Flames and smoke play and scrub with no baking, in Cycles and EEVEE, on Blender 4.5, 5.1 and 5.2. The **Simulated Fire** is a real fire simulation instead, as a normal fire, a candle or a campfire: it simulates as you play, with no bake step.

## Getting started

1. In Blender, go to **Edit > Preferences > Get Extensions**, open the small arrow at the top right, choose **Install from Disk**, and pick the zip.
2. In the 3D Viewport, press **N** and open the **Fire and Smoke** tab.
3. Click a preset, such as **Campfire**. It appears at the 3D cursor. If one of your meshes is there, such as the default cube, it hides the fire: the add-on tells you which one, so you can hide or move it.
4. Switch the viewport to **Material Preview** or **Rendered**: Solid view only shows rough shapes. The Simulated Fire is the exception: it shows in **Rendered** and **Solid**, but not in Material Preview.
5. Press play or scrub the timeline. For embers and the Simulated Fire, press play from the first frame.

To burn one of your own objects, select the mesh and click **Burning Object**. Your object isn't changed.

To remove an effect, click the bin icon on its box. Only what the add-on made for that effect is removed.

## Good to know

- **Made for mid-ground shots.** Extreme close-ups aren't supported, and top-down shots look weak: from high above, flames fade to a soft glow.
- **Face Viewport is a preview setting.** It keeps planes turned towards you as you orbit. Final renders always face the scene camera, whatever it's set to. Viewport renders follow the setting, so use Face Camera for those if your camera moves.
- **Embers replay from the start when you scrub.** They're particles, so jump back to the first frame to see them correctly. Flames and smoke don't have this limit.
- **The Simulated Fire has three presets: Normal Fire, Candle Fire and Campfire.** It starts as a Campfire. To start from another, open the **Adjust Last Operation** panel at the bottom left straight after adding it, or pick one from the **Preset** menu in the effect's box and click **Apply**. A preset is a starting point: once you change a setting, the box says **(modified)**, and Apply puts the preset's values back. Saved files keep your values, never a link to the preset.
- **The Simulated Fire plays from the first frame.** It's a real fire simulation, so it builds up as the timeline plays forward. Scrubbing back shows what it has simulated straight away. Jumping ahead, or rendering a frame it hasn't reached yet, shows no new fire: go back to the first frame and play to that frame first.
- **Flame Noise sets how erratic the Simulated Fire is.** At 0 its flames rise in calm, smooth tongues; at 1 they're the preset's; higher, they lick, split and flicker more, and burn lower. It changes the simulation, so press play from the first frame to see it.
- **You can change the Simulated Fire's look as it plays.** Its box has **Flame Colour**, **Emission Strength**, **Temperature**, **Density** and **Smoke Colour**. They show straight away, with no new simulation. White Flame Colour keeps the preset's own colours; the more vivid the colour you pick, the more the flames and their light take it. A cooler Temperature is redder and dimmer, a hotter one yellower and brighter. Apply puts the preset's look back.
- **Wind blows the Simulated Fire and embers.** Click **Wind** in the Add panel, then set its **Power**, **Gusts** and **Direction** in its box. It blows from 3 m upwind of the 3D cursor. After a change, press play from the first frame to see it. The other flames and smoke are animated, not simulated, so wind doesn't move them. Above Power 1, flames lie flat and can leave their box.
- **Fire and Smoke from Mesh sets your own mesh on fire with the Simulated Fire.** Select the mesh first, then click it in the Add panel. Your mesh isn't changed and stays visible: the fire rises from its whole surface, with every Simulated Fire setting in its box. Like the Simulated Fire, it plays from the first frame. Its box is sized around the mesh when you add it and moves with the mesh. Its presets work as the Simulated Fire's do, but they only change how the fire looks and behaves: it keeps burning from your mesh, in the same box.
- **The Simulated Fire looks its best in Cycles.** EEVEE renders it too, with a weaker look.
- **The Simulated Fire stores its simulation on disk.** As a Campfire at the default Detail it writes about 0.6 MB per frame, about 140 MB for a 250-frame timeline, and higher Detail writes more. Until you save, it goes in Blender's temporary folder, which is cleared when Blender closes. Once you save, it goes in a `fas_cache` folder beside your .blend file, in a folder of its own. Deleting the effect removes its folder. If you Save As to another folder, the old cache stays where it was and the fire simulates again into the new folder.
- **Your own smoke simulations can take the Simulated Fire's flames.** A smoke domain of yours with no **Flow** collection set takes every emitter in the scene, the Simulated Fire's included. Set that domain's **Collections > Flow** to your own collection to keep them apart. The Simulated Fire itself only ever uses its own emitter.
- **Cycles and EEVEE match with the default Real light.** The Emissive and Both options use the flames' own light, and that part is Cycles-focused.
- **Smoke carries its own shading.** It doesn't pick up scene lights or the colour of a nearby fire.
- **The add-on can change one scene setting.** Cycles draws solid black where a ray crosses too many transparent surfaces, so creating an effect raises the scene's transparent bounces when needed, and tells you. Deleting the last effect puts your value back, unless you've changed it since.

See [TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md) if something looks wrong.
