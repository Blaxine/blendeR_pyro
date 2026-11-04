# SPDX-License-Identifier: GPL-3.0-or-later
"""The release gate refuses anything short of every box ticked for this version."""

import os
import sys

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fas_testlib as lib  # noqa: E402
import release_gate  # noqa: E402

MANIFEST = 'id = "x"\nversion = "1.2.3"\n'
GOOD = "Version under test: 1.2.3\n- [x] One\n- [x] Two\n"
ALL = ["4.5", "5.1", "5.2"]
LINK = "https://example.com/issues"


def test_a_finished_checklist_passes():
    lib.check("every box ticked, right version, all Blenders", not release_gate.problems(GOOD, MANIFEST, ALL, "", LINK),
              str(release_gate.problems(GOOD, MANIFEST, ALL, "", LINK)))


def test_open_boxes_refuse():
    found = release_gate.problems("Version under test: 1.2.3\n- [x] One\n- [ ] Two\n", MANIFEST, ALL, "", LINK)
    lib.check("one open box refuses", any("Open box: Two" in p for p in found), str(found))


def test_wrong_version_refuses():
    found = release_gate.problems("Version under test: 1.2.2\n- [x] One\n", MANIFEST, ALL, "", LINK)
    lib.check("an old checklist refuses", any("1.2.2" in p for p in found), str(found))
    found = release_gate.problems("Version under test: \n- [x] One\n", MANIFEST, ALL, "", LINK)
    lib.check("a blank version refuses", bool(found), str(found))


def test_empty_checklist_refuses():
    found = release_gate.problems("Version under test: 1.2.3\n", MANIFEST, ALL, "", LINK)
    lib.check("no boxes refuses", any("no boxes" in p for p in found), str(found))


def test_missing_blender_refuses():
    found = release_gate.problems(GOOD, MANIFEST, ["5.1", "5.2"], "", LINK)
    lib.check("a missing Blender refuses", any("4.5" in p for p in found), str(found))


def test_placeholders_and_links_refuse():
    found = release_gate.problems(GOOD, MANIFEST, ALL, "NAME costs PRICE", LINK)
    lib.check("store placeholders refuse", len([p for p in found if "placeholder" in p]) == 2, str(found))
    found = release_gate.problems(GOOD, MANIFEST, ALL, "", "")
    lib.check("no support link refuses", any("support link" in p for p in found), str(found))


def test_the_real_checklist_has_every_check():
    path = os.path.join(lib.REPO, "docs", "RELEASE_CHECKLIST.md")
    with open(path, encoding="utf-8") as fh:
        text = fh.read()
    boxes = release_gate.open_boxes(text) + [
        line.strip()[6:] for line in text.splitlines() if line.strip().startswith("- [x] ")]
    eye = [b for b in boxes if b.startswith("Eye check:")]
    lib.check("36 eye checks", len(eye) == 36, str(len(eye)))
    renders_45 = [b for b in boxes if b.startswith("4.5 render:")]
    lib.check("one 4.5 render per preset", len(renders_45) == 9, str(len(renders_45)))
    from fire_and_smoke.effects import presets
    for preset_id in presets.DISPLAY_ORDER:
        label = presets.label(preset_id)
        # Whole labels, so one preset's label inside another's never counts.
        mine = [b for b in eye if b.startswith(f"Eye check: {label}, ")]
        lib.check(f"{label} is in the eye checks", len(mine) == 4, str(len(mine)))
        for version in ("5.1", "5.2"):
            for engine in ("Cycles", "EEVEE"):
                lib.check(f"{label}: {version} {engine}",
                          any(b.startswith(f"Eye check: {label}, {version}, {engine}") for b in mine))
        lib.check(f"{label} has a 4.5 render", sum(b == f"4.5 render: {label}"
                                                    or b.startswith(f"4.5 render: {label}, ")
                                                    for b in renders_45) == 1)
    sim = [b for b in eye if b.startswith("Eye check: Simulated Fire, ") and "EEVEE" in b]
    lib.check("the Simulated Fire's EEVEE boxes are judged on rendering visible fire",
              len(sim) == 2 and all("renders visible fire" in b for b in sim), str(sim))
    for needed in ("walkthrough", "built zip", "speed target", "look test"):
        lib.check(f"the checklist covers the {needed}", any(needed in b.lower() for b in boxes))


lib.main(globals())
