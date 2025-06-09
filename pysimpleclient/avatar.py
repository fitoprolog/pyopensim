from __future__ import annotations

class AvatarManager:
    """Track nearby avatars based on ObjectUpdate events."""

    def __init__(self) -> None:
        self.avatars: dict[str, tuple[float, float, float]] = {}

    def handle_event(self, event: dict) -> None:
        if event.get("event") == "ObjectUpdate" and event.get("avatar"):
            aid = str(event.get("id"))
            pos = tuple(event.get("position", (0, 0, 0)))
            self.avatars[aid] = pos
