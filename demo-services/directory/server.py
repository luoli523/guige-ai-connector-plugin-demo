"""Employee directory service (think Workday / AD), exposed over MCP.

All tools are read-only. Employee records include manager, team,
assigned devices and, for new hires, an onboarding checklist.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastmcp import FastMCP  # noqa: E402

from common.config import HOST, SERVICES  # noqa: E402
from common.store import Store  # noqa: E402

NAME = "directory"
mcp = FastMCP(NAME)
store = Store("employees.json")
READ_ONLY = {"readOnlyHint": True}


def _require(employee_id: str) -> dict:
    e = store.get(employee_id)
    if e is None:
        raise ValueError(f"employee {employee_id} not found")
    return e


def _summary(e: dict) -> dict:
    return {k: e[k] for k in ("id", "name", "email", "title", "department", "team", "location", "status")}


@mcp.tool(annotations=READ_ONLY)
def find_employee(query: str) -> list[dict]:
    """Find employees by id, name or email (case-insensitive substring).

    Returns summaries. Pass an exact id (e.g. 'E-1019') to get one match.
    """
    q = query.lower()
    return [
        _summary(e) for e in store.load()
        if q in e["id"].lower() or q in e["name"].lower() or q in e["email"].lower()
    ]


@mcp.tool(annotations=READ_ONLY)
def get_manager(employee_id: str) -> dict | None:
    """Get the direct manager of an employee. Returns null for the top of the org."""
    e = _require(employee_id)
    return _summary(_require(e["manager_id"])) if e["manager_id"] else None


@mcp.tool(annotations=READ_ONLY)
def get_team(team: str) -> list[dict]:
    """List all employees on a team (exact team name, e.g. 'Enterprise Sales')."""
    return [_summary(e) for e in store.load() if e["team"] == team]


@mcp.tool(annotations=READ_ONLY)
def get_assigned_devices(employee_id: str) -> list[dict]:
    """List devices assigned to an employee. Empty list if none."""
    return _require(employee_id)["devices"]


@mcp.tool(annotations=READ_ONLY)
def get_onboarding_status(employee_id: str | None = None) -> list[dict]:
    """Onboarding status for one employee, or for every employee currently onboarding.

    Each entry has start_date, buddy (summary or null), checklist with done flags,
    and a count of pending items. Non-onboarding employees return an empty list.
    """
    emps = [_require(employee_id)] if employee_id else store.load()
    out = []
    for e in emps:
        if e["status"] != "onboarding":
            continue
        ob = e["onboarding"]
        buddy = store.get(ob["buddy_id"]) if ob["buddy_id"] else None
        manager = store.get(e["manager_id"]) if e["manager_id"] else None
        out.append({
            **_summary(e),
            "start_date": e["start_date"],
            "manager": _summary(manager) if manager else None,
            "buddy": _summary(buddy) if buddy else None,
            "devices": e["devices"],
            "checklist": ob["checklist"],
            "pending_count": sum(1 for i in ob["checklist"] if not i["done"]),
        })
    return out


if __name__ == "__main__":
    mcp.run(transport="http", host=HOST, port=SERVICES[NAME], show_banner=False)
