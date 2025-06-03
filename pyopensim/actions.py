"""Placeholder module for viewer actions."""

class AgentActions:
    """Minimal set of avatar actions using capabilities."""

    def __init__(self, client):
        self.client = client

    def _send_movement(self, fwd=0.0, left=0.0, up=0.0):
        cap = getattr(self.client, "movement_cap", None)
        if not cap:
            print("Movement capability not available")
            return
        payload = {"forward": fwd, "left": left, "up": up}
        try:
            self.client._post(cap, payload)
        except Exception as exc:  # pragma: no cover - network
            print(f"Movement failed: {exc}")

    def walk_forward(self):
        self._send_movement(fwd=1.0)

    def turn_left(self):
        self._send_movement(left=1.0)

    def jump(self):
        self._send_movement(up=1.0)
