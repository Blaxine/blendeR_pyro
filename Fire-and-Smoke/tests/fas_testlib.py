# SPDX-License-Identifier: GPL-3.0-or-later
"""In-Blender helper shared by every Fire and Smoke test file.

Importing this module loads the add-on from the repo as the package
``fire_and_smoke`` (whatever the folder is called) and registers it.  A test
file defines ``test_*`` functions and ends with ``lib.main(globals())``;
they run in definition order in one fresh Blender process.

Rules:
  * Hold effect uuids, never entry objects, across deletions: RNA references
    into ``scene.fas_effects`` silently point at another entry after a removal.
  * Call ``bpy.context.view_layer.update()`` before measuring anything just
    created, moved or resized.
"""

import importlib.util
import os
import sys
import tempfile
import traceback

sys.dont_write_bytecode = True

import bpy  # noqa: E402

ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []


def _arg(name, default=None):
    if name in ARGS:
        i = ARGS.index(name)
        if i + 1 < len(ARGS):
            return ARGS[i + 1]
    return default


HERE = os.path.dirname(os.path.abspath(__file__))
REPO = _arg("--repo", os.path.dirname(HERE))
WORKDIR = _arg("--workdir") or tempfile.mkdtemp(prefix="fas_test_")
TAG = "FAS_TEST|"


def _load_addon():
    spec = importlib.util.spec_from_file_location(
        "fire_and_smoke", os.path.join(REPO, "__init__.py"),
        submodule_search_locations=[REPO])
    mod = importlib.util.module_from_spec(spec)
    sys.modules["fire_and_smoke"] = mod
    spec.loader.exec_module(mod)
    # What enabling the add-on does, so AddonPreferences are available.
    bpy.context.preferences.addons.new().module = "fire_and_smoke"
    mod.register()
    return mod


addon = _load_addon()

from fire_and_smoke import constants as C  # noqa: E402


def _clean(text):
    return str(text).replace("|", "/").replace("\n", " ")


def check(name, ok, detail=""):
    status = "PASS" if ok else "FAIL"
    print(f"{TAG} {status} | {_clean(name)} | {_clean(detail)}", flush=True)
    return ok


def skip(name, why):
    print(f"{TAG} SKIP | {_clean(name)} | {_clean(why)}", flush=True)


def info(text):
    print(f"{TAG} INFO | {_clean(text)}", flush=True)


def main(namespace):
    """Run every ``test_*`` function of the calling module, in order."""
    for name, fn in list(namespace.items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
            except Exception as exc:
                last = traceback.format_exc().strip().splitlines()[-3:]
                check(name, False, f"{type(exc).__name__}: {exc} @ {' / '.join(last)}")
    print(f"{TAG} DONE", flush=True)


# ---------------------------------------------------------------------------
# Scene helpers
# ---------------------------------------------------------------------------

def scene():
    return bpy.context.scene


def eevee_id():
    """BLENDER_EEVEE on 5.x, BLENDER_EEVEE_NEXT on 4.5."""
    items = bpy.types.RenderSettings.bl_rna.properties["engine"].enum_items
    return next(i.identifier for i in items if i.identifier.startswith("BLENDER_EEVEE"))


def add_camera(location=(0.0, -8.0, 1.5), look_at=(0.0, 0.0, 1.0)):
    from mathutils import Vector
    camera = bpy.data.objects.new("TestCamera", bpy.data.cameras.new("TestCamera"))
    scene().collection.objects.link(camera)
    scene().camera = camera
    camera.location = location
    camera.rotation_euler = (Vector(look_at) - Vector(location)).to_track_quat("-Z", "Y").to_euler()
    bpy.context.view_layer.update()
    return camera


def setup_render(width=160, height=90, background=(0.2, 0.2, 0.2)):
    """Cheap, plainly colour-managed renders for checks that compare pixels."""
    s = scene()
    s.render.resolution_x, s.render.resolution_y = width, height
    s.render.resolution_percentage = 100
    s.view_settings.view_transform = "Standard"
    s.view_settings.look = "None"
    s.cycles.samples = 8
    s.cycles.use_denoising = False
    s.eevee.taa_render_samples = 8
    world = s.world or bpy.data.worlds.new("TestWorld")
    s.world = world
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs[0].default_value = (*background, 1.0)


_renders = [0]


def render(engine):
    """Render to a temp PNG and return its pixels as a flat RGBA list."""
    s = scene()
    s.render.engine = engine
    _renders[0] += 1
    path = os.path.join(WORKDIR, f"render_{_renders[0]}.png")
    s.render.filepath = path
    bpy.ops.render.render(write_still=True)
    image = bpy.data.images.load(path)
    pixels = list(image.pixels)
    bpy.data.images.remove(image)
    return pixels


def mean_diff(a, b):
    return sum(abs(x - y) for x, y in zip(a, b)) / len(a)


def darkest(pixels):
    """The darkest pixel's brightest channel."""
    return min(max(pixels[i], pixels[i + 1], pixels[i + 2]) for i in range(0, len(pixels), 4))


def first_instance_facing(obj):
    """The direction the object's first instance faces, in world space."""
    from mathutils import Vector
    depsgraph = bpy.context.evaluated_depsgraph_get()
    for inst in depsgraph.object_instances:
        if inst.is_instance and inst.parent and inst.parent.original == obj:
            return (inst.matrix_world.to_3x3() @ Vector((0.0, -1.0, 0.0))).normalized()
    return None


def instance_count(obj):
    depsgraph = bpy.context.evaluated_depsgraph_get()
    return sum(1 for inst in depsgraph.object_instances
               if inst.is_instance and inst.parent and inst.parent.original == obj)
