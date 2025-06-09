from __future__ import annotations

from dataclasses import dataclass
import httpx
import xmlrpc.client

@dataclass
class LoginInfo:
    session_id: str
    agent_id: str
    seed_capability: str
    event_queue: str | None = None

async def login(login_uri: str, first: str, last: str, password: str) -> LoginInfo | None:
    payload = {
        "first": first,
        "last": last,
        "passwd": password,
        "start": "last",
        "channel": "PySimple",
        "version": "0.1",
    }
    xml = xmlrpc.client.dumps((payload,), methodname="login_to_simulator")
    headers = {"Content-Type": "text/xml"}
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(login_uri, content=xml, headers=headers)
            resp.raise_for_status()
            try:
                data = xmlrpc.client.loads(resp.content)[0][0]
            except Exception:
                data = resp.json()
        return LoginInfo(
            session_id=data.get("session_id", ""),
            agent_id=data.get("agent_id", ""),
            seed_capability=data.get("seed_capability", ""),
            event_queue=data.get("event_queue"),
        )
    except Exception:
        return None
