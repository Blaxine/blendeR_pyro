# Troubleshooting

## Black rectangles in Cycles

Too many transparent planes for the scene's limit. The add-on raises **Render Properties > Light Paths > Max Bounces > Transparent** when you create an effect, but something may have lowered it since. Set it above the total planes in your scene, or delete and re-add the effect.

## Planes look thin or turned away in the viewport

Check that the effect's **Viewport Preview** is set to **Face Viewport**. If it's set to **Face Camera**, planes face the scene camera, not your view. Final renders always face the scene camera.

## A viewport render looks different from a final render

Viewport renders follow the **Viewport Preview** setting. Choose **Face Camera** before making a viewport render with a moving camera.

## The panel says the scene has no camera

Final renders need one. Add a camera with **Add > Camera**. Viewport previews keep working without one.

## I can't see the embers

Embers are particles, so they build up from the first frame. Go to the first frame and press play: there's nothing to see on frame 1 itself. This doesn't affect flames or smoke.

They're small sparks made for mid-ground shots, and they show best against something dark. If they're still hard to see, raise **Ember Size** and **Amount** on the effect.

## I can't see the Simulated Fire

- **Is a mesh in the way?** The fire appears at the 3D cursor. If a mesh of yours is there, such as the default cube, the flames are inside it. The fire's box in the panel names the mesh: hide it (**H**) or move it, or move the 3D cursor somewhere clear before adding the fire.
- **Are you in Material Preview?** Blender's Material Preview doesn't show fluid simulations, including its own Quick Smoke. Switch the viewport to **Rendered** or **Solid**.
- **Did you play from the first frame?** It only simulates as the timeline plays forward. Go to the first frame and press play.

## The Simulated Fire looks frozen

It simulates as the timeline plays forward, one frame at a time. If you jump ahead, or skip frames, it holds the last frame it simulated. Go back to the first frame and press play: it carries on from where it got to. Frames it has already simulated show straight away when you scrub back.

After you change **Detail**, **Flame Intensity** or **Smoke Amount**, or apply a preset, go back to the first frame and play again to see the change.

## A render shows no Simulated Fire

A render of a frame the simulation hasn't reached shows no fire. Go to the first frame, play to the frame you want, then render it. To render an animation, render from the first frame.

## The Simulated Fire is slow

The first play-through simulates every frame. Lower **Detail** for a faster, coarser fire; playing the same frames again reads them from disk, which is much faster.

## My own smoke simulation shows flames I didn't add

Your smoke domain has no **Flow** collection, so it takes every emitter in the scene, including the Simulated Fire's. In your domain's **Physics > Fluid > Collections**, set **Flow** to a collection holding only your own emitters.

## My Simulated Fire says (modified)

You changed one of its settings since its preset was applied, in its box or in Blender's **Physics** panel. That's fine: the preset is only a starting point. To go back to the preset's values, pick it from the **Preset** menu and click **Apply**.

## Flames or smoke look like flat shapes

The default Solid view can't show them properly. Switch the viewport to **Material Preview** or **Rendered**. For the Simulated Fire, use **Rendered**: Material Preview doesn't show it.

## Embers look wrong after jumping along the timeline

Jump back to the first frame and play forward.

## Burning Object is refused

- **Nothing selected:** select a mesh first.
- **Part of an effect:** select one of your own meshes.
- **No faces:** the mesh has nothing to burn.
- **Over the face limit:** meshes over 2,000,000 faces are refused, since the fire rebuilds on every frame. Use a simpler copy of the mesh and hide it from the camera.

## A fire says its mesh is gone

The mesh it was burning was deleted. Delete the fire, then set a new mesh on fire.

## Top-down shots look weak

This is a known limit. Planes only spin around the vertical axis, so from high above they fade to a soft glow.

## Hard edges where flames meet an object

Flames fade out at their base, and mesh fires stand clear of the mesh, but a plane can still pass through a nearby object. Moving the effect or the object slightly usually clears it.

## Reporting a problem

When something fails, the error popup offers **Copy Report**. It lists versions and what happened, with your personal folder paths removed.
