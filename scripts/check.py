#!/usr/bin/env python3
"""Lint plugin manifests and verify cross-file references.

Checks:
  1. marketplace.json and every plugins/*/.claude-plugin/plugin.json parse.
  2. marketplace plugin sources resolve to a directory with plugin.json.
  3. Every agent plugin's agents/*.md has frontmatter with name + description.
  4. Every skills/*/SKILL.md has frontmatter with name + description,
     and name matches its directory.
  5. Agent-plugin bundled skills are byte-identical to the vertical source.
  6. Skill names referenced in agent prose (`kebab-case`) are bundled.
  7. Every plugins/*/.mcp.json URL matches demo-services/common/config.py.

Exit 0 if clean, 1 otherwise. Requires: pyyaml.
"""

import filecmp
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLUGINS = ROOT / "plugins"
errors: list[str] = []
checked = 0

try:
    import yaml
except ImportError:
    print("ERROR: requires pyyaml (pip install pyyaml)", file=sys.stderr)
    sys.exit(2)


def err(msg: str) -> None:
    errors.append(msg)


def rel(p: Path) -> str:
    return str(p.relative_to(ROOT))


def frontmatter(md: Path, required: tuple[str, ...]) -> dict | None:
    global checked
    checked += 1
    text = md.read_text(encoding="utf-8")
    if not text.startswith("---"):
        err(f"frontmatter: {rel(md)}: missing leading ---")
        return None
    try:
        _, fm, _ = text.split("---", 2)
        meta = yaml.safe_load(fm) or {}
    except (ValueError, yaml.YAMLError) as e:
        err(f"frontmatter: {rel(md)}: {e}")
        return None
    for k in required:
        if k not in meta:
            err(f"frontmatter: {rel(md)}: missing '{k}'")
    return meta


# --- 1. JSON parse ----------------------------------------------------------
for jf in [ROOT / ".claude-plugin" / "marketplace.json", *PLUGINS.glob("*/.claude-plugin/plugin.json")]:
    checked += 1
    try:
        json.loads(jf.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        err(f"JSON parse: {rel(jf)}: {e}")

# --- 2. marketplace sources -------------------------------------------------
mp = ROOT / ".claude-plugin" / "marketplace.json"
try:
    for p in json.loads(mp.read_text(encoding="utf-8")).get("plugins", []):
        checked += 1
        src = (ROOT / p["source"]).resolve()
        if not (src / ".claude-plugin" / "plugin.json").is_file():
            err(f"marketplace: {p['name']} source -> {p['source']} (no plugin.json)")
except (OSError, json.JSONDecodeError, KeyError):
    pass  # reported above or malformed entry

# --- plugin classification --------------------------------------------------
verticals = [p for p in sorted(PLUGINS.iterdir()) if (p / ".claude-plugin/plugin.json").is_file() and not (p / "agents").is_dir()]
agents = [p for p in sorted(PLUGINS.iterdir()) if (p / ".claude-plugin/plugin.json").is_file() and (p / "agents").is_dir()]

# --- 3. agent.md frontmatter -------------------------------------------------
for a in agents:
    for md in sorted((a / "agents").glob("*.md")):
        frontmatter(md, ("name", "description"))

# --- 4. SKILL.md frontmatter ------------------------------------------------
for sk in sorted(PLUGINS.glob("*/skills/*/SKILL.md")):
    meta = frontmatter(sk, ("name", "description"))
    if meta and meta.get("name") != sk.parent.name:
        err(f"skill-name: {rel(sk)}: name '{meta.get('name')}' != dir '{sk.parent.name}'")

# --- 5. bundled skills match vertical source --------------------------------
src_by_name = {sk.name: sk for v in verticals for sk in (v / "skills").glob("*") if sk.is_dir()}
for a in agents:
    for bundled in sorted((a / "skills").glob("*")):
        if not bundled.is_dir():
            continue
        checked += 1
        src = src_by_name.get(bundled.name)
        if not src:
            err(f"bundled-skill: {rel(bundled)}: no vertical source named '{bundled.name}'")
            continue
        cmp = filecmp.dircmp(src, bundled)
        if cmp.diff_files or cmp.left_only or cmp.right_only or cmp.funny_files:
            err(f"bundled-skill: {rel(bundled)}: drifted from {rel(src)} (run scripts/sync-agent-skills.py)")

# --- 6. agent prose references bundled skills -------------------------------
for a in agents:
    bundle = {p.name for p in (a / "skills").glob("*") if p.is_dir()}
    for md in sorted((a / "agents").glob("*.md")):
        for ref in set(re.findall(r"`([a-z0-9]+(?:-[a-z0-9]+)+)`", md.read_text(encoding="utf-8"))):
            if ref in src_by_name and ref not in bundle:
                err(f"agent-prose: {rel(md)}: references `{ref}` but {rel(a)}/skills/{ref}/ is not bundled")

# --- 7. .mcp.json URLs match demo-services config ---------------------------
sys.path.insert(0, str(ROOT / "demo-services"))
try:
    from common.config import SERVICES, url_for  # type: ignore
    expected = {n: url_for(n) for n in SERVICES}
except ImportError:
    expected = None
for mcp in sorted(PLUGINS.glob("*/.mcp.json")):
    checked += 1
    try:
        servers = json.loads(mcp.read_text(encoding="utf-8")).get("mcpServers", {})
    except json.JSONDecodeError as e:
        err(f"JSON parse: {rel(mcp)}: {e}")
        continue
    if expected is None:
        continue
    got = {n: s.get("url") for n, s in servers.items()}
    if got != expected:
        err(f"mcp: {rel(mcp)}: servers {got} != demo-services config {expected}")

# --- report -------------------------------------------------------------------
if errors:
    print(f"check.py: {len(errors)} error(s) in {checked} check(s)")
    for e in errors:
        print("  " + e)
    sys.exit(1)
print(f"check.py: all {checked} checks passed")
