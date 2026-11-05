# SPDX-License-Identifier: GPL-3.0-or-later
"""Fire and Smoke from Mesh: a simulated fire that burns from the buyer's mesh, which it
never changes, and that Delete cleans up.

Every check that plays the simulation steps one frame at a time from the first frame,
since Replay only simulates forward.
"""

import os
import sys

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fas_testlib as lib  # noqa: E402

import bpy  # noqa: E402
from fire_and_smoke.effects import fire_light, plane_stack, presets, sim_fire, sim_mesh_fire, sim_presets  # noqa: E402
from mathutils import Vector  # noqa: E402

PRESET = "SIMULATED_MESH_FIRE"
STATE = {}


def _tagged():
    groups = ("objects", "meshes", "lights", "materials", "node_groups", "actions", "collections")
    return [(g, i.name) for g in groups for i in getattr(bpy.data, g) if lib.C.OWNER_PROP in i.keys()]


def _entry():
    return next(e for e in lib.scene().fas_effects if e.uuid == STATE["uuid"])


def _snapshot(obj):
    """Everything of the buyer's object that the fire must never change."""
    mesh = obj.data
    return {
        "name": obj.name,
        "matrix": [tuple(row) for row in obj.matrix_world],
        "modifiers": [(m.name, m.type) for m in obj.modifiers],
        "constraints": [c.name for c in obj.constraints],
        "custom": sorted(obj.keys()),
        "groups": [(g.name, g.index) for g in obj.vertex_groups],
        "weights": [[(g.group, round(g.weight, 6)) for g in v.groups] for v in mesh.vertices],
        "data": mesh.name,
        "data_custom": sorted(mesh.keys()),
        "vertices": [tuple(round(c, 6) for c in v.co) for v in mesh.vertices],
        "materials": [m.name if m else None for m in mesh.materials],
        "hide": (obj.hide_viewport, obj.hide_render, obj.hide_get(), obj.display_type),
        "visibility": (obj.visible_camera, obj.visible_shadow, obj.visible_diffuse, obj.visible_glossy),
        "parent": obj.parent,
        "collections": sorted(c.name for c in obj.users_collection),
    }


def _play(to):
    scene = lib.scene()
    for frame in range(scene.frame_start, to + 1):
        scene.frame_set(frame)


def _flame(entry):
    """The evaluated domain's flame, summed over its two halves along x."""
    depsgraph = bpy.context.evaluated_depsgraph_get()
    settings = sim_fire.find_modifier(entry.primary.evaluated_get(depsgraph), "DOMAIN").domain_settings
    rx, ry, rz = settings.domain_resolution
    flame = settings.flame_grid
    left = right = 0.0
    for index, value in enumerate(flame):
        if index % rx < rx // 2:
            left += value
        else:
            right += value
    density = sum(settings.density_grid)
    return left, right, density


def _folder(entry):
    return os.path.realpath(bpy.path.abspath(sim_fire.domain_settings(entry).cache_directory))


def test_create():
    lib.clear_scene()
    lib.add_camera(location=(2.0, -7.0, 1.5), look_at=(2.0, 0.0, 1.2))
    lib.setup_render(width=160, height=90, background=(0.01, 0.01, 0.01))
    scene = lib.scene()
    scene.frame_start, scene.frame_end = 1, 60
    scene.frame_set(1)
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=(2.0, 0.0, 0.5))
    crate = bpy.context.object
    crate.name = "My Crate"
    crate.vertex_groups.new(name="Top").add([v.index for v in crate.data.vertices if v.co.z > 0], 1.0, "REPLACE")
    selected = set(bpy.context.selected_objects)
    STATE["crate"] = crate.name
    STATE["before"] = _snapshot(crate)

    numbers = dict((p[0], p[1]) for p in presets.PRESETS)
    lib.check("it's preset number 9", numbers[PRESET] == 9)
    order = list(presets.DISPLAY_ORDER)
    lib.check("shown straight after Burning Object", order.index(PRESET) == order.index("BURNING_OBJECT") + 1)
    lib.check("in the Fire group", presets.group(PRESET) == presets.FIRE_GROUP)
    lib.check("its label", presets.label(PRESET) == "Fire and Smoke from Mesh")

    result = bpy.ops.fas.effect_create(preset=PRESET)
    lib.check("created", result == {"FINISHED"})
    entry = scene.fas_effects[-1]
    STATE["uuid"] = entry.uuid
    lib.check("a Fire and Smoke from Mesh entry", entry.kind == lib.C.KIND_SIM_MESH_FIRE
              and entry.preset_id == PRESET, entry.kind)
    lib.check("it records the mesh it burns", entry.source == crate)
    lib.check("with 0 planes", entry.planes == 0)
    lib.check("starting from the Campfire preset", entry.sim_preset == sim_presets.CAMPFIRE
              and not sim_presets.is_modified(entry))

    domain, emitter, light = entry.primary, entry.emitter, entry.light
    bpy.context.view_layer.update()
    follow = [c for c in domain.constraints if c.type == "COPY_LOCATION"]
    lib.check("the domain follows the mesh's moves", len(follow) == 1 and follow[0].target == crate
              and follow[0].use_offset and not list(c for c in domain.constraints if c.type != "COPY_LOCATION"))
    lib.check("the domain has a scale of 1", tuple(domain.scale) == (1.0, 1.0, 1.0))
    low, high = sim_mesh_fire.world_bounds(domain)
    mesh_low, mesh_high = sim_mesh_fire.world_bounds(crate)
    lib.check("the box holds the mesh with room around it",
              all(low[i] < mesh_low[i] - 0.3 and high[i] > mesh_high[i] + 0.3 for i in (0, 1))
              and low.z <= mesh_low.z and high.z > mesh_high.z + 2.0,
              f"box {tuple(low)} to {tuple(high)}, mesh {tuple(mesh_low)} to {tuple(mesh_high)}")
    lib.check("the emitter and light are the domain's children", emitter.parent == domain and light.parent == domain)
    lib.check("the emitter is hidden from renders", emitter.hide_render)
    lib.check("the light is above the mesh", light.matrix_world.translation.z > mesh_high.z)
    copy = next((m for m in emitter.modifiers if m.type == "NODES"), None)
    lib.check("the emitter copies the mesh live", copy is not None
              and plane_stack.get_input(copy, sim_mesh_fire.SOURCE_INPUT) == crate)
    lib.check("before its flow", [m.type for m in emitter.modifiers] == ["NODES", "FLUID"])
    lib.check("the emitter's own mesh is empty", len(emitter.data.vertices) == 0)
    evaluated = emitter.evaluated_get(bpy.context.evaluated_depsgraph_get()).data
    lib.check("and it evaluates to the mesh, where it is", len(evaluated.vertices) == len(crate.data.vertices)
              and (emitter.matrix_world @ evaluated.vertices[0].co - crate.matrix_world @ crate.data.vertices[0].co).length
              < 1e-4)
    for obj in (domain, emitter, light):
        lib.check(f"{obj.name} is tagged, with its data", lib.C.OWNER_PROP in obj.keys()
                  and lib.C.OWNER_PROP in obj.data.keys())
        lib.check(f"{obj.name} sits in the effect's collection", entry.root_collection in obj.users_collection)
    lib.check("the copy's node tree is tagged", lib.C.OWNER_PROP in copy.node_group.keys())
    tags = {i[lib.C.OWNER_PROP] for g in ("objects", "meshes", "materials", "node_groups", "lights", "actions",
                                          "collections")
            for i in getattr(bpy.data, g) if lib.C.OWNER_PROP in i.keys()}
    lib.check("everything is tagged for one effect", len(tags) == 1, str(tags))

    settings = sim_fire.domain_settings(entry)
    lib.check("a Replay cache at 64 divisions", settings.cache_type == "REPLAY" and settings.resolution_max == 64)
    lib.check("taking flows and effectors from its own collection",
              settings.fluid_group == entry.root_collection and settings.effector_group == entry.root_collection)
    lib.check("over the timeline", (settings.cache_frame_start, settings.cache_frame_end) == (1, 60))
    flow = sim_fire.flow_settings(entry)
    lib.check("the emitter makes smoke and fire from its surface", flow.flow_type == "BOTH"
              and flow.flow_behavior == "INFLOW" and flow.flow_source == "MESH")

    lib.check("the selection is unchanged", set(bpy.context.selected_objects) == selected
              and bpy.context.view_layer.objects.active == crate)
    lib.check("the mesh is unchanged by Create", _snapshot(crate) == STATE["before"])


def test_it_burns_all_over():
    entry = _entry()
    _play(30)
    left, right, density = _flame(entry)
    lib.info(f"after frames 1 to 30: flame {left:.1f} left, {right:.1f} right, density {density:.1f}")
    lib.check("smoke fills the domain", density > 1.0, f"{density:.2f}")
    lib.check("there's fire", left + right > 1.0, f"{left + right:.2f}")
    lib.check("on both sides of the mesh", min(left, right) > 0.4 * max(left, right), f"{left:.1f} / {right:.1f}")


def test_a_small_cycles_render_isnt_dark():
    pixels = lib.render("CYCLES")
    bright = sum(1 for i in range(0, len(pixels), 4) if pixels[i] > 0.3)
    lib.info(f"Cycles at frame 30: {bright} bright pixels at 160x90")
    lib.check("the fire shows in Cycles", bright >= 20, str(bright))


def test_the_mesh_is_unchanged_after_playing():
    lib.check("the mesh is unchanged", _snapshot(bpy.data.objects[STATE["crate"]]) == STATE["before"])


def _replayed(frame=20):
    """Density and flame sums, and the grid's size, after playing from the first frame."""
    scene = lib.scene()
    scene.frame_set(1)
    _play(frame)
    depsgraph = bpy.context.evaluated_depsgraph_get()
    settings = sim_fire.find_modifier(_entry().primary.evaluated_get(depsgraph), "DOMAIN").domain_settings
    density, flame = list(settings.density_grid), list(settings.flame_grid)
    return sum(density), sum(flame), len(density)


def _close(a, b, tolerance=0.15):
    return abs(a - b) <= tolerance * max(abs(a), abs(b), 1e-6)


def _counting_clears(change):
    """How many times ``change`` clears this fire's cache."""
    original = sim_fire.clear_cache
    cleared = []
    sim_fire.clear_cache = lambda entry: (cleared.append(entry.uuid), original(entry))
    try:
        change()
    finally:
        sim_fire.clear_cache = original
    return cleared.count(STATE["uuid"])


def _box(entry):
    bpy.context.view_layer.update()
    low, high = sim_mesh_fire.world_bounds(entry.primary)
    return tuple(round(v, 4) for v in (*low, *high))


def test_every_simulation_setting_reaches_it():
    entry = _entry()
    base = _replayed()
    flow = sim_fire.flow_settings(entry)
    settings = sim_fire.domain_settings(entry)

    cleared = _counting_clears(lambda: setattr(_entry(), "flame_intensity", 2.5))
    lib.check("Flame Intensity reaches the fuel", abs(flow.fuel_amount - _entry().base_fuel * 2.5) < 1e-4,
              str(flow.fuel_amount))
    lib.check("and clears the cache", cleared == 1, str(cleared))
    hotter = _replayed()
    lib.check("and a replayed frame differs", not _close(hotter[1], base[1], 0.02),
              f"{hotter[1]:.1f} against {base[1]:.1f}")
    _entry().flame_intensity = 1.0

    cleared = _counting_clears(lambda: setattr(_entry(), "flame_noise", 2.0))
    entry = _entry()
    lib.check("Flame Noise reaches the swirl", abs(settings.vorticity - min(entry.base_vorticity * 2.0, 4.0)) < 1e-4
              and abs(settings.flame_vorticity - min(entry.base_flame_vorticity * 2.0, 2.0)) < 1e-4,
              f"{settings.vorticity:.3f} {settings.flame_vorticity:.3f}")
    lib.check("and clears the cache", cleared == 1, str(cleared))
    wilder = _replayed()
    lib.check("and a replayed frame differs", not _close(wilder[1], base[1], 0.02),
              f"{wilder[1]:.1f} against {base[1]:.1f}")
    _entry().flame_noise = 1.0

    cleared = _counting_clears(lambda: setattr(_entry(), "smoke_amount", 2.0))
    node = sim_fire.volume_node(_entry())
    lib.check("Smoke Amount reaches the flow's smoke", abs(flow.density - _entry().base_smoke * 2.0) < 1e-4)
    lib.check("and the material's density",
              abs(node.inputs["Density"].default_value - _entry().base_density * 2.0) < 1e-4)
    lib.check("and clears the cache", cleared == 1, str(cleared))
    smokier = _replayed()
    lib.check("and a replayed frame differs", not _close(smokier[0], base[0], 0.02),
              f"{smokier[0]:.1f} against {base[0]:.1f}")
    _entry().smoke_amount = 1.0

    cleared = _counting_clears(lambda: setattr(_entry(), "detail", 40))
    lib.check("Detail reaches the resolution", settings.resolution_max == 40)
    lib.check("and clears the cache", cleared == 1, str(cleared))
    coarse = _replayed()
    lib.check("and a replayed frame has fewer cells", coarse[2] < base[2], f"{coarse[2]} against {base[2]}")
    _entry().detail = 64
    again = _replayed()
    lib.check("back to the defaults gives the default's fire", again[2] == base[2] and _close(again[0], base[0]),
              f"{again[0]:.1f} against {base[0]:.1f}")


def test_the_look_shows_straight_away():
    entry = _entry()
    node = sim_fire.volume_node(entry)
    colour = tuple(entry.light.data.color)

    def change():
        entry = _entry()
        entry.flame_tint = (0.2, 0.5, 1.0)
        entry.emission_strength = 2.0
        entry.fire_temperature = 1.5
        entry.volume_density = 2.0
        entry.smoke_colour = (0.3, 0.1, 0.1)

    cleared = _counting_clears(change)
    entry = _entry()
    lib.check("the look sliders keep the cache", cleared == 0, str(cleared))
    lib.check("Density reaches the material",
              abs(node.inputs["Density"].default_value - entry.base_density * 2.0) < 1e-4)
    lib.check("Smoke Colour reaches the material",
              all(abs(a - b) < 1e-4 for a, b in zip(node.inputs["Color"].default_value, (0.3, 0.1, 0.1))))
    lib.check("Emission Strength reaches the blackbody",
              abs(node.inputs["Blackbody Intensity"].default_value - entry.base_blackbody * 2.0) < 1e-4)
    lib.check("Temperature reaches the material", abs(node.inputs["Temperature"].default_value - 1500.0) < 1e-2)
    _ramp, strength, tint, _heat = sim_fire.flame_nodes(entry)
    lib.check("Flame Colour reaches the flames",
              all(abs(a - b) < 1e-4 for a, b in zip(sim_fire._socket(tint.inputs, "B_Color").default_value,
                                                    (0.2, 0.5, 1.0))))
    lib.check("and the fire light", tuple(entry.light.data.color) != colour)
    lib.check("and the preset says (modified)", sim_presets.is_modified(entry))
    entry.flame_tint, entry.smoke_colour = (1.0, 1.0, 1.0), (0.05, 0.05, 0.05)
    entry.emission_strength = entry.fire_temperature = entry.volume_density = 1.0


def test_the_light():
    entry = _entry()
    domain, light = entry.primary, entry.light
    lib.check("Real is the default", entry.light_mode == "REAL" and not light.hide_render)
    lib.check("Real hides the domain from diffuse and glossy rays",
              not domain.visible_diffuse and not domain.visible_glossy)
    entry.light_mode = "EMISSIVE"
    lib.check("Emissive turns the light off", light.hide_render)
    lib.check("and lets the flames light the scene", domain.visible_diffuse and domain.visible_glossy)
    _entry().light_mode = "REAL"
    energy = fire_light.get_energy(light.data)
    _entry().light_strength = 2.0
    lib.check("Light Strength reaches the light", abs(fire_light.get_energy(light.data) - energy * 2.0) < 1e-3)
    _entry().light_strength = 1.0


def test_presets_keep_the_box():
    entry = _entry()
    box, light_at = _box(entry), tuple(entry.light.location)
    entry.sim_preset_choice = sim_presets.CANDLE_FIRE
    result = bpy.ops.fas.apply_sim_preset(uuid=STATE["uuid"])
    entry = _entry()
    candle = sim_presets.CATALOG[sim_presets.CANDLE_FIRE]
    lib.check("Candle Fire applies", result == {"FINISHED"} and entry.sim_preset == sim_presets.CANDLE_FIRE
              and entry.sim_preset_label == "Candle Fire")
    lib.check("its behaviour reaches the fire", abs(sim_fire.domain_settings(entry).burning_rate
                                                    - candle["domain"]["burning_rate"]) < 1e-4
              and sim_fire.flow_settings(entry).flow_type == candle["flow"]["flow_type"])
    lib.check("and its detail", sim_fire.domain_settings(entry).resolution_max == candle["entry"]["detail"])
    lib.check("the box stays fitted to the mesh", _box(entry) == box, f"{_box(entry)} / {box}")
    lib.check("the emitter still copies the mesh", len(entry.emitter.data.vertices) == 0
              and [m.type for m in entry.emitter.modifiers] == ["NODES", "FLUID"])
    lib.check("the light stays above the mesh", tuple(entry.light.location) == light_at)
    lib.check("it isn't (modified)", not sim_presets.is_modified(entry))
    entry.flame_intensity = 1.5
    lib.check("an edit marks it (modified)", sim_presets.is_modified(_entry()))
    entry = _entry()
    entry.sim_preset_choice = sim_presets.CAMPFIRE
    bpy.ops.fas.apply_sim_preset(uuid=STATE["uuid"])
    entry = _entry()
    lib.check("Campfire applies back, with the sliders reset", entry.sim_preset == sim_presets.CAMPFIRE
              and entry.flame_intensity == 1.0 and not sim_presets.is_modified(entry))
    lib.check("and the box is still the same", _box(entry) == box)
    lib.check("the mesh is unchanged by Apply", _snapshot(bpy.data.objects[STATE["crate"]]) == STATE["before"])


def test_timeline_and_wind():
    from fire_and_smoke.core import handlers
    scene = lib.scene()
    settings = sim_fire.domain_settings(_entry())
    handlers.note_ranges()
    scene.frame_end = 120
    handlers.follow_ranges()
    lib.check("a longer timeline lengthens the simulation",
              (settings.cache_frame_start, settings.cache_frame_end) == (1, 120))
    scene.frame_end = 60
    handlers.follow_ranges()
    lib.check("and back", (settings.cache_frame_start, settings.cache_frame_end) == (1, 60))
    cleared = _counting_clears(lambda: bpy.ops.fas.wind_create())
    lib.check("adding wind makes it simulate again", cleared >= 1, str(cleared))
    wind = scene.fas_effects[-1]
    cleared = _counting_clears(lambda: setattr(wind, "wind_power", 0.8))
    lib.check("and so does changing it", cleared >= 1, str(cleared))
    bpy.ops.fas.effect_delete(uuid=scene.fas_effects[-1].uuid)
    scene.frame_set(1)


def _corner_smoke(frame=20):
    """Smoke in the box's low front-left corner, away from the burning mesh."""
    scene = lib.scene()
    scene.frame_set(1)
    _play(frame)
    depsgraph = bpy.context.evaluated_depsgraph_get()
    settings = sim_fire.find_modifier(_entry().primary.evaluated_get(depsgraph), "DOMAIN").domain_settings
    rx, ry, rz = settings.domain_resolution
    total = 0.0
    for index, value in enumerate(settings.density_grid):
        x, y, z = index % rx, (index // rx) % ry, index // (rx * ry)
        if x < rx * 0.3 and y < ry * 0.3 and z < rz * 0.25:
            total += value
    return total


def test_its_own_flows_only():
    scene = lib.scene()
    base = _corner_smoke()
    # A buyer's own flow in a corner of the box, beside the burning mesh.
    bpy.ops.mesh.primitive_cube_add(size=0.25, location=(1.15, -0.85, 0.15))
    theirs = bpy.context.object
    fluid = theirs.modifiers.new("Fluid", "FLUID")
    fluid.fluid_type = "FLOW"
    fluid.flow_settings.flow_type = "BOTH"
    fluid.flow_settings.flow_behavior = "INFLOW"
    sim_fire.clear_cache(_entry())
    scoped = _corner_smoke()
    settings = sim_fire.domain_settings(_entry())
    settings.fluid_group = None
    sim_fire.clear_cache(_entry())
    unscoped = _corner_smoke()
    lib.info(f"smoke in the corner: alone {base:.1f}, with a buyer's flow there {scoped:.1f}, unscoped {unscoped:.1f}")
    lib.check("a buyer's flow inside its box changes nothing", _close(scoped, base, 0.05),
              f"{scoped:.1f} against {base:.1f}")
    lib.check("the control: unscoped, it would take it", unscoped > base * 1.5 + 1.0,
              f"{unscoped:.1f} against {base:.1f}")
    settings.fluid_group = _entry().root_collection
    sim_fire.clear_cache(_entry())
    bpy.data.objects.remove(theirs)
    bpy.context.view_layer.objects.active = bpy.data.objects[STATE["crate"]]
    scene.frame_set(1)


def test_it_refuses_plainly():
    count = len(lib.scene().fas_effects)
    before = set(_tagged())
    for what, active, words in (("nothing selected", None, "Select a mesh"),
                                ("one of its own parts", _entry().primary, "part of an effect")):
        bpy.context.view_layer.objects.active = active
        try:
            result = bpy.ops.fas.effect_create(preset=PRESET)
        except RuntimeError as exc:
            result = {"CANCELLED"}
            lib.check(f"refuses {what} plainly", words in str(exc), str(exc)[:120])
        lib.check(f"refuses {what}", result == {"CANCELLED"})
    lib.check("nothing half-built is left", len(lib.scene().fas_effects) == count and set(_tagged()) == before)
    bpy.context.view_layer.objects.active = bpy.data.objects[STATE["crate"]]


def test_delete_cleans_up():
    entry = _entry()
    folder = _folder(entry)
    lib.check("the cache folder exists before Delete", os.path.isdir(folder))
    bpy.ops.fas.effect_delete(uuid=STATE["uuid"])
    lib.check("nothing tagged left", not _tagged(), str(_tagged()))
    lib.check("Delete removes the effect's cache folder", not os.path.exists(folder), folder)
    crate = bpy.data.objects.get(STATE["crate"])
    lib.check("the mesh stays, exactly as it was", crate is not None and _snapshot(crate) == STATE["before"])
    lib.check("and it's still in the scene", crate.name in lib.scene().objects)


def test_a_moved_mesh_gets_a_box_where_it_is():
    """The box is placed from the mesh's world bounds, whatever its origin and scale."""
    crate = bpy.data.objects[STATE["crate"]]
    crate.location = (-3.0, 1.0, 2.0)
    crate.scale = (2.0, 1.0, 0.5)
    bpy.context.view_layer.update()
    bpy.ops.fas.effect_create(preset=PRESET)
    entry = lib.scene().fas_effects[-1]
    bpy.context.view_layer.update()
    low, high = sim_mesh_fire.world_bounds(entry.primary)
    mesh_low, mesh_high = sim_mesh_fire.world_bounds(crate)
    centre, mesh_centre = (low + high) * 0.5, (mesh_low + mesh_high) * 0.5
    lib.check("the box is centred on the mesh", (Vector((centre.x, centre.y)) - Vector((mesh_centre.x, mesh_centre.y))
                                                 ).length < 1e-4, f"{tuple(centre)} / {tuple(mesh_centre)}")
    lib.check("and starts at its foot", abs(low.z - mesh_low.z) < 0.2 * (mesh_high - mesh_low).length,
              f"{low.z:.3f} / {mesh_low.z:.3f}")
    bpy.ops.fas.effect_delete(uuid=entry.uuid)
    lib.check("and it deletes cleanly", not _tagged(), str(_tagged()))


lib.main(globals())
