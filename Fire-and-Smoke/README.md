# Fire and Smoke

Add fire, smoke, smoke columns and embers to a Blender scene from presets. Flames and smoke play and scrub with no baking, in Cycles and EEVEE, on Blender 4.5, 5.1 and 5.2.

## Getting started

1. In Blender, go to **Edit > Preferences > Get Extensions**, open the small arrow at the top right, choose **Install from Disk**, and pick the zip.
2. In the 3D Viewport, press **N** and open the **Fire and Smoke** tab.
3. Click a preset, such as **Campfire**. It appears at the 3D cursor.
4. Switch the viewport to **Material Preview** or **Rendered**: Solid view only shows rough shapes.
5. Press play or scrub the timeline. For embers, press play from the first frame.

To burn one of your own objects, select the mesh and click **Burning Object**. Your object isn't changed.

To remove an effect, click the bin icon on its box. Only what the add-on made for that effect is removed.

## Good to know

- **Made for mid-ground shots.** Extreme close-ups aren't supported, and top-down shots look weak: from high above, flames fade to a soft glow.
- **Face Viewport is a preview setting.** It keeps planes turned towards you as you orbit. Final renders always face the scene camera, whatever it's set to. Viewport renders follow the setting, so use Face Camera for those if your camera moves.
- **Embers replay from the start when you scrub.** They're particles, so jump back to the first frame to see them correctly. Flames and smoke don't have this limit.
- **Cycles and EEVEE match with the default Real light.** The Emissive and Both options use the flames' own light, and that part is Cycles-focused.
- **Smoke carries its own shading.** It doesn't pick up scene lights or the colour of a nearby fire.
- **The add-on can change one scene setting.** Cycles draws solid black where a ray crosses too many transparent surfaces, so creating an effect raises the scene's transparent bounces when needed, and tells you. Deleting the last effect puts your value back, unless you've changed it since.

See [TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md) if something looks wrong.
