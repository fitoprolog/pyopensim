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

    def walk_backward(self):
        self._send_movement(fwd=-1.0)

    def strafe_left(self):
        self._send_movement(left=1.0)

    def strafe_right(self):
        self._send_movement(left=-1.0)

    def turn_left(self):
        self._send_movement(left=1.0)

    def turn_right(self):
        self._send_movement(left=-1.0)

    def jump(self):
        self._send_movement(up=1.0)

    def fly_up(self):
        self._send_movement(up=1.0)

    def fly_down(self):
        self._send_movement(up=-1.0)

    def touch(self, object_id: str):
        cap = getattr(self.client, "seed_capability", None)
        if not cap:
            print("Touch capability not available")
            return
        url = f"{cap}/touch"
        try:
            self.client._post(url, {"id": object_id})
        except Exception as exc:  # pragma: no cover - network
            print(f"Touch failed: {exc}")
