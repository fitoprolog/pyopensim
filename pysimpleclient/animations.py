from __future__ import annotations

class Animations:
    """Play simple animations via capability."""

    def __init__(self) -> None:
        self.active: set[str] = set()

    async def play(self, http, cap: str, anim_id: str) -> None:
        await http.post(cap, json={"animation": anim_id, "action": "start"})
        self.active.add(anim_id)

    async def stop(self, http, cap: str, anim_id: str) -> None:
        await http.post(cap, json={"animation": anim_id, "action": "stop"})
        self.active.discard(anim_id)
