"""Knowledge base service (think Confluence), exposed over MCP.

All tools are read-only. Articles have Markdown bodies; some are
archived and superseded, so callers should check status and updated_at.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastmcp import FastMCP  # noqa: E402

from common.config import HOST, SERVICES  # noqa: E402
from common.store import Store  # noqa: E402

NAME = "knowledge-base"
mcp = FastMCP(NAME)
store = Store("articles.json")
READ_ONLY = {"readOnlyHint": True}


@mcp.tool(annotations=READ_ONLY)
def search_articles(query: str, include_archived: bool = True) -> list[dict]:
    """Search articles by keyword in title, tags and body (case-insensitive).

    Returns id, title, tags, status, updated_at and a short snippet, ranked
    title match > tag match > body match. Archived articles are included by
    default so callers can see that a newer version exists; check status.
    """
    q = query.lower()
    hits = []
    for a in store.load():
        if not include_archived and a["status"] == "archived":
            continue
        if q in a["title"].lower():
            rank = 0
        elif any(q in t.lower() for t in a["tags"]):
            rank = 1
        elif q in a["body"].lower():
            rank = 2
        else:
            continue
        body = a["body"]
        i = body.lower().find(q)
        snippet = body[max(0, i - 60): i + 100].replace("\n", " ") if i >= 0 else body[:160].replace("\n", " ")
        hits.append((rank, {
            "id": a["id"], "title": a["title"], "tags": a["tags"],
            "status": a["status"], "updated_at": a["updated_at"], "snippet": snippet,
        }))
    # same rank: newest first, so a superseding article beats its archived predecessor
    hits.sort(key=lambda h: h[1]["updated_at"], reverse=True)
    hits.sort(key=lambda h: h[0])
    return [h for _, h in hits]


@mcp.tool(annotations=READ_ONLY)
def get_article(article_id: str) -> dict:
    """Get one article with its full Markdown body. article_id like 'KB-104'."""
    a = store.get(article_id)
    if a is None:
        raise ValueError(f"article {article_id} not found")
    return a


if __name__ == "__main__":
    mcp.run(transport="http", host=HOST, port=SERVICES[NAME], show_banner=False)
