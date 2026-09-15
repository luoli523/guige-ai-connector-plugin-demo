#!/usr/bin/env python3
"""Re-sync each agent plugin's bundled skills from the vertical-plugin source.

Under plugins/, a plugin with an agents/ directory is an agent plugin; the
rest are vertical plugins. Agent plugins bundle vendored copies of vertical
skills under skills/<name>/. The vertical copy is the source of truth; run
this after editing a skill there.

Usage:
    python3 scripts/sync-agent-skills.py            # sync existing bundles
    python3 scripts/sync-agent-skills.py --all      # also bundle every vertical skill
                                                    # into every agent plugin
"""

import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLUGINS = ROOT / "plugins"


def plugin_dirs() -> tuple[list[Path], list[Path]]:
    verticals, agents = [], []
    for p in sorted(PLUGINS.iterdir()):
        if not (p / ".claude-plugin" / "plugin.json").is_file():
            continue
        (agents if (p / "agents").is_dir() else verticals).append(p)
    return verticals, agents


def main(argv: list[str]) -> int:
    bundle_all = "--all" in argv
    verticals, agents = plugin_dirs()
    src_by_name: dict[str, Path] = {}
    for v in verticals:
        for sk in sorted((v / "skills").glob("*")):
            if (sk / "SKILL.md").is_file():
                src_by_name[sk.name] = sk

    synced, missing = 0, []
    for a in agents:
        sk_dir = a / "skills"
        sk_dir.mkdir(exist_ok=True)
        names = set(src_by_name) if bundle_all else {p.name for p in sk_dir.iterdir() if p.is_dir()}
        for name in sorted(names):
            src = src_by_name.get(name)
            if not src:
                missing.append(f"{sk_dir.relative_to(ROOT)}/{name}")
                continue
            dst = sk_dir / name
            if dst.exists():
                shutil.rmtree(dst)
            shutil.copytree(src, dst)
            synced += 1

    print(f"synced {synced} bundled skill dir(s) into {len(agents)} agent plugin(s)")
    if missing:
        print("no vertical source for:", *missing, sep="\n  ", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
