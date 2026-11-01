# Fire and Smoke Thesaurus

The project's ubiquitous-language reference. Code, docs, panel text and requirement plans use these terms with exactly these meanings. Add a term here before introducing it anywhere else.

| Term | Definition | Notes |
| ---- | ---------- | ----- |
| Active Camera | The Geometry Nodes input that gives the scene's current camera. | Works in a modifier. |
| AquaSuite | The owner's separate paid water add-on for Blender, sold to the same beginners. | Source of code copied once; no runtime dependency. |
| Bounce limit | The scene's transparent bounces value as the add-on manages it: raised above the scene's plane total, restored only while still the value the add-on set. | |
| Cycles | Blender's path-tracing render engine. | Limited by `cycles.transparent_max_bounces`. |
| EEVEE | Blender's real-time render engine. | Engine id `BLENDER_EEVEE` on 5.1 and 5.2. |
| Effect | Everything one Create builds: objects, node tree, material, light and collection, tracked and deleted as one unit. | Recorded in `Scene.fas_effects`. |
| Extension | Blender's add-on package format, described by `blender_manifest.toml` and built into a zip. | `blender --command extension build`. |
| Geometry Nodes | Blender's node system for generating geometry, run here through a modifier. | |
| Instancer attribute | An Attribute node mode that reads data stored on an instance. | Works in Cycles and EEVEE. |
| Is Viewport | The Geometry Nodes input that is true during viewport evaluation and false in a final render. | Works in a modifier. |
| Legacy particle system | Blender's older particle system, `ParticleSettings` on an object. | Available on 5.1 and 5.2. |
| Light mode | How a fire lights its scene: Real (the owned light), Emissive (the planes) or Both. | Real is the default and the only engine-matched mode. |
| Look test | The owner's by-eye judgement of the Campfire in a fixed scene and moving shot. | Recorded in `docs/LOOK_TEST.md`. |
| Plane stack | The camera-facing planes of an effect, built with Geometry Nodes. | Sites times layers planes. |
| Release gate | The checklist every version must finish before it ships. | `docs/RELEASE_CHECKLIST.md`. |
| Transparent bounces | The Cycles limit on transparent surfaces a ray may cross, `cycles.transparent_max_bounces`. | Default 8; a ray that reaches it draws black. |
| View sync | The Python timer that feeds the most recently moved viewport's position to the view target. | Preview only. |
| View target | The add-on-owned empty per scene that planes face in Face Viewport. | Reaches each effect through a modifier input. |
| Viewport Transform | The Geometry Nodes input that gives the 3D viewport's view. | Tool context only; errors in a modifier. |
