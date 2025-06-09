from __future__ import annotations

import asyncio
import contextlib
from typing import Optional, Any

import httpx

from .login import login, LoginInfo
from .avatar import AvatarManager
from .inventory import Inventory
from .animations import Animations
from .simulator import Simulator


class SimpleClient:
    """Very small client combining login and event handling."""

    def __init__(self, login_uri: str) -> None:
        self.login_uri = login_uri
        self.http = httpx.AsyncClient(timeout=10)
        self.login_info: Optional[LoginInfo] = None
        self.avatar = AvatarManager()
        self.inventory = Inventory()
        self.animations = Animations()
        self.simulator = Simulator()
        self._event_task: Optional[asyncio.Task] = None

    async def login(self, first: str, last: str, password: str) -> bool:
        info = await login(self.login_uri, first, last, password)
        if not info:
            return False
        self.login_info = info
        if info.event_queue:
            self._event_task = asyncio.create_task(self._event_loop(info.event_queue))
        return True

    async def disconnect(self) -> None:
        if self._event_task:
            self._event_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._event_task
        await self.http.aclose()
        self.login_info = None

    async def _event_loop(self, url: str) -> None:
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

    def _handle_event(self, event: dict) -> None:
        self.avatar.handle_event(event)
        self.simulator.handle_event(event)
