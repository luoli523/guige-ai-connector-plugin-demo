#!/usr/bin/env python3
"""Start every service, call every tool once, assert key results, restore data.

Usage: uv run smoke_test.py
Exit 0 when all checks pass. tickets.json is restored to its pre-run
content even if a check fails, so the repo copy stays the "factory" state.
"""

import asyncio
import socket
import subprocess
import sys
import time
from pathlib import Path

from fastmcp import Client

from common.config import HOST, SERVICES, url_for
from common.store import Store

ROOT = Path(__file__).resolve().parent
failures: list[str] = []


def check(label: str, cond: bool, detail: str = "") -> None:
    print(("ok   " if cond else "FAIL ") + label + (f"  ({detail})" if detail and not cond else ""))
    if not cond:
        failures.append(label)


async def call(service: str, tool: str, **kw):
    async with Client(url_for(service)) as c:
        r = await c.call_tool(tool, kw)
        return r.data if r.data is not None else r.structured_content


async def expect_error(service: str, tool: str, **kw) -> bool:
    try:
        await call(service, tool, **kw)
        return False
    except Exception:
        return True


def wait_ready(timeout: float = 15.0) -> None:
    deadline = time.time() + timeout
    pending = set(SERVICES)
    while pending and time.time() < deadline:
        for name in list(pending):
            try:
                socket.create_connection((HOST, SERVICES[name]), timeout=1.0).close()
                pending.discard(name)
            except OSError:
                pass
        time.sleep(0.3)
    if pending:
        raise RuntimeError(f"services not ready: {', '.join(sorted(pending))}")


async def run_checks() -> None:
    # tool inventory + read/write annotation
    expected_ro = {
        "ticketing": {"search_tickets": True, "get_ticket": True, "create_ticket": False,
                      "update_ticket_status": False, "add_comment": False},
        "directory": {"find_employee": True, "get_manager": True, "get_team": True,
                      "get_assigned_devices": True, "get_onboarding_status": True},
        "knowledge-base": {"search_articles": True, "get_article": True},
    }
    for name, want in expected_ro.items():
        async with Client(url_for(name)) as c:
            got = {t.name: bool(t.annotations and t.annotations.read_only_hint) for t in await c.list_tools()}
        check(f"{name}: tools and readOnlyHint", got == want, str(got))

    # ticketing reads
    t = await call("ticketing", "get_ticket", ticket_id="T-1042")
    check("T-1042 is 米粉妹's open mailbox ticket",
          t["requester_id"] == "E-1019" and t["status"] == "open" and "邮箱" in t["title"])
    dup = await call("ticketing", "search_tickets", query="键盘")
    check("duplicate keyboard tickets found", {x["id"] for x in dup} == {"T-1037", "T-1038"})
    check("search excludes comments", all("comments" not in x for x in dup))
    hi = await call("ticketing", "search_tickets", priority="high", status="open")
    check("one open high-priority ticket", [x["id"] for x in hi] == ["T-1035"])

    # directory
    e = await call("directory", "find_employee", query="E-1019")
    check("find E-1019", len(e) == 1 and e[0]["name"] == "米粉妹")
    check("E-1019 manager is 猪肉荣", (await call("directory", "get_manager", employee_id="E-1019"))["name"] == "猪肉荣")
    check("CEO has no manager", await call("directory", "get_manager", employee_id="E-1001") in (None, {"result": None}))
    check("Enterprise Sales has 4", len(await call("directory", "get_team", team="Enterprise Sales")) == 4)
    check("E-1020 has no devices", await call("directory", "get_assigned_devices", employee_id="E-1020") == [])
    ob = await call("directory", "get_onboarding_status")
    check("three onboarding employees", {o["id"] for o in ob} == {"E-1019", "E-1020", "E-1021"})
    check("E-1020 has no buddy", next(o for o in ob if o["id"] == "E-1020")["buddy"] is None)
    check("active employee has no onboarding", await call("directory", "get_onboarding_status", employee_id="E-1011") == [])

    # knowledge base
    pw = await call("knowledge-base", "search_articles", query="密码")
    ids = [a["id"] for a in pw]
    check("KB-112 ranks above archived KB-102", ids.index("KB-112") < ids.index("KB-102"), str(ids))
    check("archived flag visible", next(a for a in pw if a["id"] == "KB-102")["status"] == "archived")
    auth = await call("knowledge-base", "search_articles", query="认证不通过")
    check("auth failure maps to KB-109 and KB-104", {a["id"] for a in auth} == {"KB-109", "KB-104"})
    check("get_article returns body", "MFA" in (await call("knowledge-base", "get_article", article_id="KB-109"))["body"])

    # ticketing writes
    w = await call("ticketing", "update_ticket_status", ticket_id="T-1042", status="waiting_on_requester", assignee_id="E-1007")
    check("status change reports before/after",
          w["before"] == {"status": "open", "assignee_id": None}
          and w["after"] == {"status": "waiting_on_requester", "assignee_id": "E-1007"})
    w = await call("ticketing", "add_comment", ticket_id="T-1042", author_id="E-1007", body="smoke")
    check("comment appended", w["after"]["comment_count"] == 1)
    w = await call("ticketing", "create_ticket", title="smoke", description="x", requester_id="E-1011")
    check("create_ticket assigns next id", w["after"]["id"] == "T-1048")
    check("write persisted", (await call("ticketing", "get_ticket", ticket_id="T-1042"))["status"] == "waiting_on_requester")

    # error paths
    check("unknown ticket errors", await expect_error("ticketing", "get_ticket", ticket_id="T-9"))
    check("bad status errors", await expect_error("ticketing", "update_ticket_status", ticket_id="T-1042", status="nope"))
    check("unknown employee errors", await expect_error("directory", "get_manager", employee_id="E-9"))
    check("unknown article errors", await expect_error("knowledge-base", "get_article", article_id="KB-9"))


def main() -> int:
    tickets_path = Store("tickets.json").path
    snapshot = tickets_path.read_bytes()
    proc = subprocess.Popen([sys.executable, str(ROOT / "run_all.py")],
                            cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        wait_ready()
        asyncio.run(run_checks())
    finally:
        proc.terminate()
        proc.wait(timeout=10)
        tickets_path.write_bytes(snapshot)
        print("restored", tickets_path.name)
    if failures:
        print(f"\n{len(failures)} check(s) failed: {', '.join(failures)}")
        return 1
    print("\nall checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
