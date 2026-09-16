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
  8. Agent frontmatter `tools` entries that name MCP tools use the runtime
     prefix mcp__plugin_<plugin>_<server>__ and point at a server declared
     in that plugin's .mcp.json.
  9. OpenAI marketplace matches the Claude catalog; native manifests share
     names, versions, skills and MCP files, with valid presentation metadata.

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
agent_meta: list[tuple[Path, Path, dict]] = []
for a in agents:
    for md in sorted((a / "agents").glob("*.md")):
        meta = frontmatter(md, ("name", "description"))
        if meta:
            agent_meta.append((a, md, meta))

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

# --- 8. agent tools use the plugin-prefixed MCP names -----------------------
# Claude Code registers a plugin's MCP server as plugin_<plugin>_<server>, so
# its tools are mcp__plugin_<plugin>_<server>__<tool>. A bare mcp__<server>__*
# matches nothing and the agent refuses to start with zero tools.
for a, md, meta in agent_meta:
    tools = meta.get("tools")
    if not tools:
        continue
    if isinstance(tools, str):
        tools = [t.strip() for t in tools.split(",") if t.strip()]
    try:
        declared = set(json.loads((a / ".mcp.json").read_text(encoding="utf-8")).get("mcpServers", {}))
    except (OSError, json.JSONDecodeError):
        declared = set()
    for t in tools:
        if not t.startswith("mcp__"):
            continue
        checked += 1
        m = re.fullmatch(rf"mcp__plugin_{re.escape(a.name)}_([A-Za-z0-9-]+)__.+", t)
        if not m:
            err(f"agent-tools: {rel(md)}: '{t}' must look like mcp__plugin_{a.name}_<server>__*")
        elif m.group(1) not in declared:
            err(f"agent-tools: {rel(md)}: '{t}' names server '{m.group(1)}' not in {rel(a / '.mcp.json')}")

# --- 9. OpenAI compatibility ------------------------------------------------
def read_object(path: Path) -> dict:
    global checked
    checked += 1
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(value, dict):
            raise ValueError("expected a JSON object")
        return value
    except (OSError, ValueError) as e:
        err(f"JSON: {rel(path)}: {e}")
        return {}


claude_catalog = read_object(ROOT / ".claude-plugin/marketplace.json")
openai_catalog = read_object(ROOT / ".agents/plugins/marketplace.json")
if openai_catalog.get("name") != claude_catalog.get("name"):
    err("openai-marketplace: name differs from Claude marketplace")
interface = openai_catalog.get("interface")
if not isinstance(interface, dict) or not interface.get("displayName"):
    err("openai-marketplace: missing interface.displayName")
entries = openai_catalog.get("plugins", [])
if not isinstance(entries, list) or not all(isinstance(p, dict) for p in entries):
    err("openai-marketplace: plugins must be an array of objects")
    entries = []
if [p.get("name") for p in entries] != [p.get("name") for p in claude_catalog.get("plugins", [])]:
    err("openai-marketplace: plugin names/order differ from Claude marketplace")
for entry in entries:
    name = entry.get("name")
    if not isinstance(name, str) or not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", name):
        err("openai-marketplace: invalid plugin name")
        continue
    plugin = PLUGINS / name
    if entry.get("source") != {"source": "local", "path": f"./plugins/{name}"}:
        err(f"openai-marketplace: {name}: expected local source ./plugins/{name}")
    policy = entry.get("policy")
    if not isinstance(policy, dict) or policy.get("installation") not in (
        "AVAILABLE", "NOT_AVAILABLE", "INSTALLED_BY_DEFAULT"
    ) or policy.get("authentication") not in ("ON_INSTALL", "ON_USE"):
        err(f"openai-marketplace: {name}: invalid installation/authentication policy")
    if entry.get("category") != "Productivity":
        err(f"openai-marketplace: {name}: expected Productivity category")
    native = read_object(plugin / ".codex-plugin/plugin.json")
    claude = read_object(plugin / ".claude-plugin/plugin.json")
    if native.get("name") != name or native.get("version") != claude.get("version"):
        err(f"openai-plugin: {name}: name/version differ from Claude plugin")
    for field, expected_path in (("skills", "./skills/"), ("mcpServers", "./.mcp.json")):
        if native.get(field) != expected_path or not (plugin / expected_path).exists():
            err(f"openai-plugin: {name}: {field} must reference existing {expected_path}")
    if any(field in native for field in ("agents", "commands", "apps", "hooks", "displayName")):
        err(f"openai-plugin: {name}: unsupported field for this local compatibility package")
    author = native.get("author")
    if not native.get("description") or not isinstance(author, dict) or not author.get("name"):
        err(f"openai-plugin: {name}: missing description/author.name")
    ui = native.get("interface")
    if not isinstance(ui, dict):
        err(f"openai-plugin: {name}: missing interface object")
        continue
    for field in ("displayName", "shortDescription", "longDescription", "developerName", "category"):
        if not isinstance(ui.get(field), str) or not ui[field].strip():
            err(f"openai-plugin: {name}: missing interface.{field}")
    prompts = ui.get("defaultPrompt")
    if not isinstance(prompts, list) or not 1 <= len(prompts) <= 3 or not all(
        isinstance(p, str) and 0 < len(p.strip()) <= 128 for p in prompts
    ):
        err(f"openai-plugin: {name}: defaultPrompt needs 1–3 nonempty strings, max 128 characters each")
    if ui.get("capabilities") != ["Read", "Write"]:
        err(f"openai-plugin: {name}: expected Read/Write capabilities")

# --- report -------------------------------------------------------------------
if errors:
    print(f"check.py: {len(errors)} error(s) in {checked} check(s)")
    for e in errors:
        print("  " + e)
    sys.exit(1)
print(f"check.py: all {checked} checks passed")
