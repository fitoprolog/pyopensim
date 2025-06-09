from __future__ import annotations

from dataclasses import dataclass
import httpx

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
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(login_uri, data=payload)
            resp.raise_for_status()
            data = resp.json()
        return LoginInfo(
            session_id=data.get("session_id", ""),
            agent_id=data.get("agent_id", ""),
            seed_capability=data.get("seed_capability", ""),
            event_queue=data.get("event_queue"),
        )
    except Exception:
        return None
