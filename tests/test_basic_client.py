import asyncio
import os
import sys
from types import SimpleNamespace

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pylibremetaverse.basic as basic
import pytest
import xmlrpc.client

class FakeResponse:
    def __init__(self, data):
        self.data = data
        self.status_code = 200
    def raise_for_status(self):
        pass
    def json(self):
        if isinstance(self.data, bytes):
            raise ValueError("binary")
        return self.data
    @property
    def content(self):
        if isinstance(self.data, bytes):
            return self.data
        return str(self.data).encode()

class FakeClient:
    def __init__(self, responses):
        self.responses = responses
        self.calls = []
    async def post(self, url, data=None, json=None, content=None, headers=None):
        self.calls.append(("post", url, data, json, content, headers))
        return FakeResponse(self.responses.pop(0))
    async def get(self, url):
        self.calls.append(("get", url))
        return FakeResponse(self.responses.pop(0))
    async def aclose(self):
        pass

def test_login_and_event_loop(monkeypatch):
    async def run_test():
        login_dict = {
            "session_id": "sess",
            "agent_id": "agent",
            "seed_capability": "http://seed",
            "event_queue": "http://events",
        }
        login_data = xmlrpc.client.dumps((login_dict,), methodresponse=True)
        event_data = {"events": [{"event": "ObjectUpdate", "id": 1, "position": [1,2,3]}]}
        fake_http = FakeClient([login_data, event_data])
        monkeypatch.setattr(basic, "httpx", SimpleNamespace(AsyncClient=lambda timeout: fake_http))

        client = basic.BasicClient("http://login")
        assert await client.login("First", "Last", "pw")
        # Let event loop run once
        await asyncio.sleep(0)
        await client.disconnect()
        assert client.scene.get("1") == (1,2,3)

    asyncio.run(run_test())
