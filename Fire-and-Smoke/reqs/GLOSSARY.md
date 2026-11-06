# Fire and Smoke Thesaurus

The project's ubiquitous-language reference. Code, docs, panel text and requirement plans use these terms with exactly these meanings. Add a term here before introducing it anywhere else.

| Term | Definition | Notes |
| ---- | ---------- | ----- |
| Active Camera | The Geometry Nodes input that gives the scene's current camera. | Works in a modifier. |
| AquaSuite | The owner's separate paid water add-on for Blender, sold to the same beginners. | Source of code copied once; no runtime dependency. |
| Bounce limit | The scene's transparent bounces value as the add-on manages it: raised above the scene's plane total, restored only while still the value the add-on set. | |
| Burn From | Fire and Smoke from Mesh's choice of where it burns: Whole Mesh, or one of the mesh's vertex groups. Painted weights set how strongly each part burns. | Stored as the group's name in `burn_from`, empty for Whole Mesh; the menu `burn_from_choice` is a view of it. The emitter's own group list mirrors the mesh's names in order, since the flow reads its group by position in the mesh's weights. |
| Size correction | Fire and Smoke from Mesh's scaling of a preset to the mesh's size, measured once at Create: time runs with the square root of the size, the burn slows with it, the material thins and the light grows with the area. | `sim_mesh_fire.corrected`, applied by Apply; the size is `mesh_size` on the entry. Tuned in `docs/LOOK_TEST.md`. |
| Cache folder | The folder a Simulated Fire's Replay cache is written to: `fas_cache/<uuid>` in Blender's session temp folder while the .blend is unsaved, and beside the .blend once it's saved. | Delete removes it only after the path check. |
| Cycles | Blender's path-tracing render engine. | Limited by `cycles.transparent_max_bounces`. |
| Detail | The Simulated Fire's control for its domain's resolution, in divisions along the domain's longest side. | 64 by default; higher is slower and uses more disk space. |
| Domain | The box a Mantaflow simulation runs in, and the Simulated Fire's primary object. | Takes flows and effectors only from its own collection. |
| EEVEE | Blender's real-time render engine. | Engine id `BLENDER_EEVEE` on 5.1 and 5.2. |
| Effect | Everything one Create builds: objects, node tree, material, light and collection, tracked and deleted as one unit. | Recorded in `Scene.fas_effects`. |
| Extension | Blender's add-on package format, described by `blender_manifest.toml` and built into a zip. | `blender --command extension build`. |
| Flame colour | The Simulated Fire's ramp from its flame to its emission colour: dark red at the edges to a pale yellow core. | The Campfire uses it at strength 7; at 0 a flame shows only its blackbody glow. |
| Live copy | Fire and Smoke from Mesh's emitter: an owned object with an empty mesh whose Geometry Nodes modifier outputs the source mesh's evaluated geometry, posed and deformed, through Object Info in Relative space. | The Fluid flow emits from it. Its vertex group list mirrors the source's names in order, for Burn From. |
| Look sliders | The Simulated Fire's Flame Colour, Emission Strength, Temperature, Density and Smoke Colour: volume material settings, so a change needs no new simulation. | Part of the preset snapshot; Apply resets them. |
| Flame Noise | The Simulated Fire's slider for how erratic its flames are: it scales the domain's vorticity and flame vorticity from the preset's. | Clears the cache. Blender caps flame vorticity at 2. |
| Flow | A Mantaflow emitter: the object a simulated fire's flames and smoke come from. | The Simulated Fire's is a disc, or the Campfire's log patches, the domain's child, hidden from renders. |
| Geometry Nodes | Blender's node system for generating geometry, run here through a modifier. | |
| Instancer attribute | An Attribute node mode that reads data stored on an instance. | Works in Cycles and EEVEE. |
| Is Viewport | The Geometry Nodes input that is true during viewport evaluation and false in a final render. | Works in a modifier. |
| Legacy particle system | Blender's older particle system, `ParticleSettings` on an object. | Available on 5.1 and 5.2. |
| Light mode | How a fire lights its scene: Real (the owned light), Emissive (the planes) or Both. | Real is the default and the only engine-matched mode. |
| Look test | The owner's by-eye judgement of the Campfire in a fixed scene and moving shot. | Recorded in `docs/LOOK_TEST.md`. |
| Plane stack | The camera-facing planes of an effect, built with Geometry Nodes. | Sites times layers planes. |
| Release gate | The checklist every version must finish before it ships. | `docs/RELEASE_CHECKLIST.md`. |
| Replay cache | Mantaflow's cache type that simulates forward as the timeline plays, with no bake step. | Only adds frames in order: a jump holds the last simulated frame. |
| Simulated Fire | The preset, number 8 (id `SIMULATED_CAMPFIRE`), that builds a real Mantaflow fire: an owned domain, emitter, volume material and fire light. | Effect kind `SIM_FIRE`. Called the Simulated Fire before it had simulation presets. |
| Fire and Smoke from Mesh | The preset, number 9 (id `SIMULATED_MESH_FIRE`), that burns a real Mantaflow fire from the buyer's selected mesh. Its owned emitter reads the mesh live, so the mesh is never changed. | Effect kind `SIM_MESH_FIRE`. With the Simulated Fire, one of the simulated kinds (`SIM_KINDS`). Its box is fitted to the mesh at Create and follows the mesh with Copy Location. |
| Simulation preset | One of the Simulated Fire's own presets, Normal Fire (1), Candle Fire (2) and Campfire (3): plain data applied once, at Create or with Apply. | The effect stores a snapshot of what was applied, and shows (modified) once it no longer matches. Saved files never reference the definitions. |
| Source mesh | The buyer's mesh that Fire and Smoke from Mesh burns, recorded as the entry's `source`. | Never changed: no modifier, constraint, tag or vertex group is added to it. The box's Copy Location follows it. |
| Transparent bounces | The Cycles limit on transparent surfaces a ray may cross, `cycles.transparent_max_bounces`. | Default 8; a ray that reaches it draws black. |
| View sync | The Python timer that feeds the most recently moved viewport's position to the view target. | Preview only. |
| View target | The add-on-owned empty per scene that planes face in Face Viewport. | Reaches each effect through a modifier input. |
| Wind | The effect, kind `WIND`, that adds an owned Plane Wind force field with Power, Gusts and Direction. | Power 1 is strength 0.25. Blows the Simulated Fire and embers, not plane fires. |
| Viewport Transform | The Geometry Nodes input that gives the 3D viewport's view. | Tool context only; errors in a modifier. |
