"""Ticketing service (think Jira Service Desk), exposed over MCP.

Read tools: search_tickets, get_ticket
Write tools: create_ticket, update_ticket_status, add_comment
Write tools return {"before": ..., "after": ...} so the caller can show
the change to a human before/after confirming.
"""

import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastmcp import FastMCP  # noqa: E402

from common.config import HOST, SERVICES  # noqa: E402
from common.store import Store  # noqa: E402

NAME = "ticketing"
STATUSES = ("open", "in_progress", "waiting_on_requester", "resolved")
PRIORITIES = ("low", "medium", "high")
CATEGORIES = ("it", "hr")

mcp = FastMCP(NAME)
store = Store("tickets.json")
READ_ONLY = {"readOnlyHint": True}


def _now() -> str:
    return datetime.now(timezone(timedelta(hours=8))).isoformat(timespec="seconds")


def _require(ticket_id: str) -> tuple[list[dict], dict]:
    tickets = store.load()
    for t in tickets:
        if t["id"] == ticket_id:
            return tickets, t
    raise ValueError(f"ticket {ticket_id} not found")


@mcp.tool(annotations=READ_ONLY)
def search_tickets(
    query: str = "",
    status: str | None = None,
    category: str | None = None,
    priority: str | None = None,
    requester_id: str | None = None,
    created_after: str | None = None,
) -> list[dict]:
    """Search tickets. All filters are optional and ANDed together.

    query matches title and description (case-insensitive substring).
    created_after is an ISO date/datetime; tickets created on or after it are returned.
    Returns summaries without comments; call get_ticket for full detail.
    """
    q = query.lower()
    out = []
    for t in store.load():
        if q and q not in t["title"].lower() and q not in t["description"].lower():
            continue
        if status and t["status"] != status:
            continue
        if category and t["category"] != category:
            continue
        if priority and t["priority"] != priority:
            continue
        if requester_id and t["requester_id"] != requester_id:
            continue
        if created_after and t["created_at"] < created_after:
            continue
        out.append({k: v for k, v in t.items() if k != "comments"})
    return out


@mcp.tool(annotations=READ_ONLY)
def get_ticket(ticket_id: str) -> dict:
    """Get one ticket with its full comment history. ticket_id like 'T-1042'."""
    return _require(ticket_id)[1]


@mcp.tool
def create_ticket(
    title: str,
    description: str,
    requester_id: str,
    category: str = "it",
    priority: str = "medium",
) -> dict:
    """Create a new ticket in status 'open'. Returns the created ticket."""
    if category not in CATEGORIES:
        raise ValueError(f"category must be one of {CATEGORIES}")
    if priority not in PRIORITIES:
        raise ValueError(f"priority must be one of {PRIORITIES}")
    tickets = store.load()
    now = _now()
    ticket = {
        "id": store.next_id("T-"),
        "title": title,
        "description": description,
        "category": category,
        "priority": priority,
        "status": "open",
        "requester_id": requester_id,
        "assignee_id": None,
        "created_at": now,
        "updated_at": now,
        "comments": [],
    }
    tickets.append(ticket)
    store.save(tickets)
    return {"before": None, "after": ticket}


@mcp.tool
def update_ticket_status(
    ticket_id: str, status: str, assignee_id: str | None = None
) -> dict:
    """Change a ticket's status and optionally assign it.

    status must be one of: open, in_progress, waiting_on_requester, resolved.
    Returns {"before": {...}, "after": {...}} with the changed fields only.
    """
    if status not in STATUSES:
        raise ValueError(f"status must be one of {STATUSES}")
    tickets, t = _require(ticket_id)
    before = {"status": t["status"], "assignee_id": t["assignee_id"]}
    t["status"] = status
    if assignee_id is not None:
        t["assignee_id"] = assignee_id
    t["updated_at"] = _now()
    store.save(tickets)
    return {"id": ticket_id, "before": before,
            "after": {"status": t["status"], "assignee_id": t["assignee_id"]}}


@mcp.tool
def add_comment(ticket_id: str, author_id: str, body: str) -> dict:
    """Append a comment to a ticket. Returns the ticket's new comment count and the comment."""
    tickets, t = _require(ticket_id)
    comment = {"author_id": author_id, "body": body, "created_at": _now()}
    before = len(t["comments"])
    t["comments"].append(comment)
    t["updated_at"] = t["comments"][-1]["created_at"]
    store.save(tickets)
    return {"id": ticket_id, "before": {"comment_count": before},
            "after": {"comment_count": before + 1, "comment": comment}}


if __name__ == "__main__":
    mcp.run(transport="http", host=HOST, port=SERVICES[NAME], show_banner=False)
