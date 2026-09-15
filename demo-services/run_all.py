#!/usr/bin/env python3
"""Start every demo service defined in common/config.py.

Usage:
    uv run run_all.py            # start all, Ctrl-C stops all
    uv run run_all.py ticketing  # start a subset

Each service is `<name>/server.py` run as a child process.
"""

import signal
import subprocess
import sys
from pathlib import Path

from common.config import SERVICES, url_for

ROOT = Path(__file__).resolve().parent


def main(names: list[str]) -> int:
    unknown = [n for n in names if n not in SERVICES]
    if unknown:
        print(f"unknown service(s): {', '.join(unknown)}. "
              f"Known: {', '.join(SERVICES)}", file=sys.stderr)
        return 2
    targets = names or list(SERVICES)

    procs: list[subprocess.Popen] = []
    for name in targets:
        server = ROOT / name / "server.py"
        if not server.is_file():
            print(f"skip {name}: {server.relative_to(ROOT)} not found", file=sys.stderr)
            continue
        procs.append(subprocess.Popen([sys.executable, str(server)], cwd=ROOT))
        print(f"{name:<15} {url_for(name)}")

    if not procs:
        return 1

    def stop(*_):
        for p in procs:
            p.terminate()

    signal.signal(signal.SIGINT, stop)
    signal.signal(signal.SIGTERM, stop)
    for p in procs:
        p.wait()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
