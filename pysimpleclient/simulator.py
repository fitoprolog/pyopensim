from __future__ import annotations

class Simulator:
    """Maintain a simple representation of nearby objects."""

    def __init__(self) -> None:
        self.objects: dict[str, tuple[float, float, float]] = {}

    def handle_event(self, event: dict) -> None:
        if event.get("event") == "ObjectUpdate":
            oid = str(event.get("id"))
            pos = tuple(event.get("position", (0, 0, 0)))
            self.objects[oid] = pos
