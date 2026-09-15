"""Single place that defines which service listens on which port.

`run_all.py` starts every entry here; `plugins/*/.mcp.json` must point at
the same host/port. Change ports here, then update .mcp.json to match.
"""

HOST = "127.0.0.1"

# service directory name -> port
SERVICES: dict[str, int] = {
    "ticketing": 8001,
    "directory": 8002,
    "knowledge-base": 8003,
}


def url_for(name: str) -> str:
    return f"http://{HOST}:{SERVICES[name]}/mcp"
