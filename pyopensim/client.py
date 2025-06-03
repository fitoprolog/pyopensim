"""Client for connecting to OpenSimulator/SecondLife grids."""

try:
    import requests
except ImportError:  # pragma: no cover - optional dependency
    requests = None

class OpenSimClient:
    def __init__(self, login_uri: str, username: str, password: str, first: str, last: str):
        self.login_uri = login_uri
        self.username = username
        self.password = password
        self.first = first
        self.last = last
        self.session_info = None

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
            self.session_info = resp.json()
            return True
        except Exception as exc:
            print(f"Login failed: {exc}")
            return False

    def disconnect(self):
        self.session_info = None

    def is_connected(self) -> bool:
        return self.session_info is not None
