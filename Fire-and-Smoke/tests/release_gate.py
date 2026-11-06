# SPDX-License-Identifier: GPL-3.0-or-later
"""The release gate: a version ships only with every box ticked, for that version.

Plain Python, no Blender: ``run_tests.py --release`` uses it.
"""

import re

REQUIRED_BLENDERS = ("4.5", "5.1", "5.2")
PLACEHOLDER_TERMS = ("NAME", "PRICE", "SUPPORT LINK")


def manifest_version(manifest_text):
    match = re.search(r'^version\s*=\s*"([^"]+)"', manifest_text, flags=re.M)
    return match.group(1) if match else None


def open_boxes(checklist_text):
    return [line.strip()[6:] for line in checklist_text.splitlines()
            if line.strip().startswith("- [ ] ")]


def problems(checklist_text, manifest_text, blender_names, store_text="", support_url=""):
    """Everything stopping this version from shipping, as sentences.  Empty means go."""
    found = []
    version = manifest_version(manifest_text)
    match = re.search(r"^Version under test:[ 	]*(\S*)", checklist_text, flags=re.M)
    under_test = match.group(1) if match else ""
    if under_test != version:
        found.append(f"The checklist is for version '{under_test or 'none'}', but the manifest says {version}")
    if not re.search(r"^- \[[ x]\] ", checklist_text, flags=re.M):
        found.append("The checklist has no boxes")
    found += [f"Open box: {box}" for box in open_boxes(checklist_text)]
    for name in REQUIRED_BLENDERS:
        if name not in blender_names:
            found.append(f"Blender {name} isn't in the test config")
    for term in PLACEHOLDER_TERMS:
        if term in store_text:
            found.append(f"The store text still has the placeholder {term}")
    if not support_url:
        found.append("There's no support link yet: create the public issues repo, then set SUPPORT_URL")
    return found
