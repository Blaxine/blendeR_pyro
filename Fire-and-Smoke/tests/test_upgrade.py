# SPDX-License-Identifier: GPL-3.0-or-later
"""Upgrading in one Blender session: when Blender re-runs __init__.py over a
version that was turned off, the add-on must use the new files throughout."""

import importlib
import os
import shutil
import sys

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fas_testlib as lib  # noqa: E402

import bpy  # noqa: E402

NAME = "fas_upgrade_copy"
SKIP = {"tests", "docs", "requirements", "look_test_output", "__pycache__"}


def test_new_files_replace_the_old_modules():
    # Only one copy of the add-on's classes can be registered at a time.
    lib.addon.unregister()
    pkg = os.path.join(lib.WORKDIR, NAME)
    os.makedirs(pkg)
    for item in os.listdir(lib.REPO):
        source = os.path.join(lib.REPO, item)
        if os.path.isdir(source) and item not in SKIP and not item.startswith("."):
            shutil.copytree(source, os.path.join(pkg, item),
                            ignore=shutil.ignore_patterns("__pycache__"))
        elif item.endswith((".py", ".toml")):
            shutil.copy(source, pkg)
    sys.path.insert(0, lib.WORKDIR)
    mod = importlib.import_module(NAME)
    bpy.context.preferences.addons.new().module = NAME
    mod.register()
    mod.unregister()
    lib.check("the old version's modules are still loaded after turning it off",
              NAME + ".constants" in sys.modules
              and not hasattr(sys.modules[NAME + ".constants"], "NEW_IN_THIS_VERSION"))

    with open(os.path.join(pkg, "constants.py"), "a", encoding="utf-8") as fh:
        fh.write("\nNEW_IN_THIS_VERSION = True\n")
    with open(os.path.join(pkg, "core", "bounces.py"), "a", encoding="utf-8") as fh:
        fh.write("\nSEEN_NEW = C.NEW_IN_THIS_VERSION\n")
    importlib.invalidate_caches()
    importlib.reload(mod)  # what addon_utils.enable does when the file changed
    lib.check("the package attribute is the new constants",
              getattr(mod.C, "NEW_IN_THIS_VERSION", False))
    lib.check("submodules read the new constants too",
              getattr(sys.modules.get(NAME + ".core.bounces"), "SEEN_NEW", False))
    mod.register()
    lib.check("the new version registers and runs",
              bpy.ops.fas.campfire_create() == {"FINISHED"})
    mod.unregister()


lib.main(globals())
