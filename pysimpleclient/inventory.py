from __future__ import annotations

class Inventory:
    """Very small inventory container."""

    def __init__(self) -> None:
        self.items: dict[str, dict] = {}

    def update(self, items: dict[str, dict]) -> None:
        self.items.update(items)
