# SPDX-License-Identifier: GPL-3.0-or-later
"""The extension zip: validates, builds, ships only add-on files, installs into a
temporary user folder and runs there.  Installs never touch real add-ons:
BLENDER_USER_RESOURCES points every install at a temp folder."""

import os
import subprocess
import sys
import zipfile

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fas_testlib as lib  # noqa: E402

import bpy  # noqa: E402

FORBIDDEN = ("requirements/", "tests/", ".git", "__pycache__", "look_test_output",
             "docs/THESAURUS.md", "docs/LOOK_TEST.md", "docs/RELEASE_CHECKLIST.md", "docs/STORE_PAGE.md")
REQUIRED = ("__init__.py", "blender_manifest.toml", "constants.py", "core/bounces.py",
            "effects/plane_stack.py", "effects/presets.py", "ui/panel.py",
            "README.md", "docs/TROUBLESHOOTING.md")
PRIVATE_REPO = "blender_pyro"

RUN_SCRIPT = r'''
import addon_utils, bpy
addon_utils.enable("bl_ext.user_default.fire_and_smoke", default_set=False)
result = bpy.ops.fas.campfire_create()
print("ZIPRUN", result == {"FINISHED"})
'''


def _blender(*args, env=None):
    proc = subprocess.run([bpy.app.binary_path, "--factory-startup", *args],
                          capture_output=True, text=True, encoding="utf-8",
                          errors="replace", timeout=300, env=env)
    return proc.returncode, proc.stdout + proc.stderr


def _temp_user_env():
    resources = os.path.join(lib.WORKDIR, "user_resources")
    os.makedirs(resources, exist_ok=True)
    return dict(os.environ, BLENDER_USER_RESOURCES=resources), resources


def test_package():
    code, out = _blender("--command", "extension", "validate", lib.REPO)
    lib.check("manifest validates", code == 0 and "Success" in out, out.strip()[-200:])

    out_dir = os.path.join(lib.WORKDIR, "dist")
    os.makedirs(out_dir, exist_ok=True)
    code, out = _blender("--command", "extension", "build",
                         "--source-dir", lib.REPO, "--output-dir", out_dir)
    zips = [f for f in os.listdir(out_dir) if f.endswith(".zip")]
    lib.check("extension zip builds", code == 0 and len(zips) == 1, out.strip()[-200:])
    if not zips:
        return
    path = os.path.join(out_dir, zips[0])
    with zipfile.ZipFile(path) as zf:
        names = zf.namelist()
        leaks = [n for n in names if PRIVATE_REPO in zf.read(n).decode("utf-8", "ignore").lower()]
    lib.check("nothing in the zip mentions the private repo", not leaks, str(leaks))
    bad = [n for n in names if any(n.startswith(f) or f"/{f}" in f"/{n}" for f in FORBIDDEN)
           or n.endswith(".zip")]
    lib.check("zip ships no plans, tests, git or internal docs", not bad, str(bad[:10]))
    missing = [r for r in REQUIRED if r not in names]
    lib.check("zip contains the add-on", not missing, f"missing {missing}")

    env, resources = _temp_user_env()
    code, out = _blender("--command", "extension", "install-file", "-r", "user_default",
                         "--enable", path, env=env)
    lib.check("zip installs", code == 0, out.strip()[-300:])
    found = any("fire_and_smoke" in dirs for _root, dirs, _files in os.walk(resources))
    lib.check("install landed in the temp folder", found)

    code, out = _blender("-b", "--python-expr", RUN_SCRIPT, env=env)
    ran = [ln for ln in out.splitlines() if ln.startswith("ZIPRUN")]
    lib.check("installed add-on enables and creates a Campfire",
              code == 0 and ran == ["ZIPRUN True"],
              f"exit {code}: " + (ran or [out.strip()[-300:]])[0])


lib.main(globals())
