"""Client for connecting to OpenSimulator/SecondLife grids."""

from typing import Optional
import threading
import time

try:  # pragma: no cover - optional dependency
    import requests as _requests
except ImportError:  # pragma: no cover - missing dependency
    _requests = None

if _requests is None:
    class _RequestsPlaceholder:
        """Fallback object so tests can monkeypatch ``requests`` methods."""

        def post(self, *_, **__):
            raise ImportError("requests is required for HTTP operations")

        def get(self, *_, **__):
            raise ImportError("requests is required for HTTP operations")

    requests = _RequestsPlaceholder()
else:
    requests = _requests

from .scene import Scene

class OpenSimClient:
    def __init__(self, login_uri: str, username: str, password: str, first: str, last: str):
        self.login_uri = login_uri
        self.username = username
        self.password = password
        self.first = first
        self.last = last
        self.session_info: Optional[dict] = None
        self.session_id: Optional[str] = None
        self.agent_id: Optional[str] = None
        self.seed_capability: Optional[str] = None
        self.event_queue_cap: Optional[str] = None
        self.movement_cap: Optional[str] = None
        self.scene = Scene()
        self._event_thread: Optional[threading.Thread] = None
        self._running = False

    def login(self) -> bool:
        """Attempt to login to the grid using a simple HTTP request.

        This is a simplified placeholder for the actual login sequence used by
        real SecondLife/OpenSim viewers. Real viewers perform complex LLSD
        negotiation which is out of scope for this skeleton.
        """
        if requests is None:
            raise ImportError("requests is required for login functionality")

        payload = {
            "first": self.first,
            "last": self.last,
            "passwd": self.password,
            "start": "last",
            "channel": "PyOpenSim",
            "version": "0.0.1",
        }
        try:
            resp = requests.post(self.login_uri, data=payload, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            self.session_info = data
            self.session_id = data.get("session_id")
            self.agent_id = data.get("agent_id")
            self.seed_capability = data.get("seed_capability")
            self.event_queue_cap = data.get("event_queue")
            self.movement_cap = data.get("movement" )
            if self.event_queue_cap:
                self._running = True
                self._event_thread = threading.Thread(target=self._event_loop, daemon=True)
                self._event_thread.start()
            return True
        except Exception as exc:  # pragma: no cover - network errors
            print(f"Login failed: {exc}")
            return False

    def disconnect(self):
        self._running = False
        if self._event_thread and self._event_thread.is_alive():
            self._event_thread.join(timeout=1)
        self.session_info = None

    def is_connected(self) -> bool:
        return self.session_info is not None

    # internal helpers -------------------------------------------------
    def _post(self, url: str, data: dict):
        if requests is None:
            raise ImportError("requests is required")
        resp = requests.post(url, json=data, timeout=10)
        resp.raise_for_status()
        return resp.json()

    def _event_loop(self):
        while self._running and self.event_queue_cap:
            try:
                resp = requests.get(self.event_queue_cap, timeout=30)
                resp.raise_for_status()
                events = resp.json().get("events", [])
                for ev in events:
                    self._handle_event(ev)
            except Exception as exc:  # pragma: no cover - network
                print(f"Event loop error: {exc}")
                time.sleep(1)

    def _handle_event(self, event: dict):
        etype = event.get("event")
        if etype == "ObjectUpdate":
            obj_id = event.get("id")
            pos = tuple(event.get("position", (0, 0, 0)))
            rot = tuple(event.get("rotation", (0, 0, 0)))
            self.scene.update_object(str(obj_id), pos, rot)
