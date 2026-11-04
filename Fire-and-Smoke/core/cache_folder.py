# SPDX-License-Identifier: GPL-3.0-or-later
"""Where a simulated effect keeps its cache, and when the add-on may remove it.

Each effect has its own folder named after its uuid, inside a folder called
``fas_cache``: in Blender's session temp folder while the .blend is unsaved, and beside
the .blend once it's saved.  A relative ``//`` path in an unsaved file resolves against
Blender's working directory, so an unsaved file always gets an absolute temp path.

Saving re-points every domain to the rule's path, and so does opening a file: Save As
to another folder rewrites relative paths to point back at the old folder, which stays
where it was.

Delete removes a folder only when its name is the effect's uuid, its parent is called
``fas_cache``, and it resolves inside the .blend's folder or the session temp folder.
Anything else stays on disk.
"""

import os
import shutil

import bpy

from .. import constants as C


def saved_path(effect_uuid):
    return f"//{C.CACHE_FOLDER}/{effect_uuid}"


def temp_path(effect_uuid):
    return os.path.join(bpy.app.tempdir, C.CACHE_FOLDER, effect_uuid)


def path_for(effect_uuid):
    """The folder the path rule gives this effect now, as Blender stores it."""
    return saved_path(effect_uuid) if bpy.data.filepath else temp_path(effect_uuid)


def _absolute(path):
    return bpy.path.abspath(path) if path.startswith("//") else path


def _roots():
    roots = [bpy.app.tempdir]
    if bpy.data.filepath:
        roots.append(os.path.dirname(bpy.data.filepath))
    return [os.path.normcase(os.path.realpath(r)) for r in roots if r]


def _inside(path, root):
    try:
        return path != root and os.path.commonpath([path, root]) == root
    except ValueError:  # different drives
        return False


def removable(path, effect_uuid):
    """True only for this effect's own folder, as the path check defines it."""
    if not path or not effect_uuid:
        return False
    absolute = _absolute(path)
    if not os.path.isabs(absolute) or os.path.islink(absolute.rstrip("\\/")):
        return False
    real = os.path.realpath(absolute)
    if os.path.basename(real) != effect_uuid:
        return False
    if os.path.basename(os.path.dirname(real)) != C.CACHE_FOLDER:
        return False
    real = os.path.normcase(real)
    return any(_inside(real, root) for root in _roots())


def candidates(effect_uuid, current=""):
    """Every folder this effect may have written to: its current path, and the rule's
    folders under both roots, since saving moves it from one to the other."""
    found = []
    for path in (current, temp_path(effect_uuid), saved_path(effect_uuid) if bpy.data.filepath else ""):
        if path and path not in found:
            found.append(path)
    return found


def remove(effect_uuid, current=""):
    """Remove the effect's folders that pass the path check.  Returns what was removed."""
    removed = []
    for path in candidates(effect_uuid, current):
        if not removable(path, effect_uuid):
            continue
        real = os.path.realpath(_absolute(path))
        if os.path.isdir(real):
            try:
                shutil.rmtree(real)
                removed.append(real)
            except OSError as exc:
                print(f"[{C.DISPLAY_NAME}] couldn't remove a cache folder: {exc}")
    return removed


# ---------------------------------------------------------------------------
# Domains
# ---------------------------------------------------------------------------

def domain_settings(obj):
    """The Fluid domain settings on an effect's primary, or None."""
    if obj is None:
        return None
    modifier = next((m for m in obj.modifiers if m.type == "FLUID" and m.fluid_type == "DOMAIN"), None)
    return modifier.domain_settings if modifier is not None else None


def simulated(scene):
    """Every Simulated Fire entry in the scene whose domain is still there, with its settings."""
    for entry in scene.fas_effects:
        if entry.kind != C.KIND_SIM_FIRE:
            continue
        settings = domain_settings(entry.primary)
        if settings is not None:
            yield entry, settings


def repoint(entry, settings=None, wanted=None):
    """Give the domain the path the rule gives now.  The folder at the old path stays.
    Returns True if the path changed."""
    settings = settings or domain_settings(entry.primary)
    if settings is None:
        return False
    wanted = wanted or path_for(entry.uuid)
    if settings.cache_directory == wanted:
        return False
    settings.cache_directory = wanted
    return True


def repoint_all(saved=False):
    """Every simulated fire in every scene.  ``saved``: use the saved rule whatever
    ``bpy.data.filepath`` says, for a file that's being saved right now."""
    changed = 0
    for scene in bpy.data.scenes:
        for entry, settings in list(simulated(scene)):
            changed += repoint(entry, settings, saved_path(entry.uuid) if saved else None)
    return changed
