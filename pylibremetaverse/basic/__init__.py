"""Simplified Python implementation of key LibreMetaverse features.

This module provides an asynchronous client capable of logging into a
Second Life/OpenSim grid using the LLSD login API, retrieving events
through the event queue capability and sending simple chat messages.
The code is intentionally minimal but functional so tests can exercise
basic behaviour without requiring the huge auto-generated port.
"""

from __future__ import annotations

from dataclasses import dataclass
import asyncio
from contextlib import suppress
from typing import Any, Optional, Dict

try:
    import httpx
except ImportError:  # pragma: no cover - optional
    httpx = None  # type: ignore


@dataclass
class LoginResponse:
    """Data returned by a successful login."""

    session_id: str
    agent_id: str
    seed_capability: str
    event_queue: Optional[str] = None


class BasicClient:
    """Minimal asynchronous client for LibreMetaverse style interactions."""

    def __init__(self, login_uri: str) -> None:
        if httpx is None:
            raise ImportError("httpx is required for network operations")
        self.login_uri = login_uri
        self.http = httpx.AsyncClient(timeout=10)
        self.login_data: Optional[LoginResponse] = None
        self._event_task: Optional[asyncio.Task] = None
        self.scene: Dict[str, Any] = {}

    async def login(self, first: str, last: str, password: str) -> bool:
        """Perform LLSD login and start event processing."""
        payload = {
            "first": first,
            "last": last,
            "passwd": password,
            "start": "last",
            "channel": "PyLibreMetaverse",
            "version": "0.1",
        }
        try:
            resp = await self.http.post(self.login_uri, data=payload)
            resp.raise_for_status()
            data = resp.json()
            self.login_data = LoginResponse(
                session_id=data.get("session_id", ""),
                agent_id=data.get("agent_id", ""),
                seed_capability=data.get("seed_capability", ""),
                event_queue=data.get("event_queue"),
            )
            if self.login_data.event_queue:
                self._event_task = asyncio.create_task(self._event_loop())
            return True
        except Exception:
            return False

    async def disconnect(self) -> None:
        """Stop event processing and close the HTTP client."""
        if self._event_task:
            self._event_task.cancel()
            with suppress(asyncio.CancelledError):
                await self._event_task
            self._event_task = None
        await self.http.aclose()
        self.login_data = None

    async def send_chat(self, message: str, channel: int = 0) -> None:
        """Send a chat message via the seed capability."""
        if not self.login_data:
            raise RuntimeError("Not logged in")
        url = f"{self.login_data.seed_capability}/chat"
        await self.http.post(url, json={"message": message, "channel": channel})

    async def _event_loop(self) -> None:
        assert self.login_data and self.login_data.event_queue
        url = self.login_data.event_queue
        while True:
            try:
                resp = await self.http.get(url)
                resp.raise_for_status()
                events = resp.json().get("events", [])
                for ev in events:
                    self._handle_event(ev)
            except asyncio.CancelledError:
                break
            except Exception:
                await asyncio.sleep(1)

    def _handle_event(self, event: Dict[str, Any]) -> None:
        if event.get("event") == "ObjectUpdate":
            obj_id = str(event.get("id"))
            pos = tuple(event.get("position", (0, 0, 0)))
            self.scene[obj_id] = pos

__all__ = ["BasicClient", "LoginResponse"]
