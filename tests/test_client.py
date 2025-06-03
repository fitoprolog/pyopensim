import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from pyopensim.client import OpenSimClient


def test_client_initial_state():
    client = OpenSimClient('http://example.com', 'user', 'pass', 'First', 'Last')
    assert not client.is_connected()


def test_login_parses_response(monkeypatch):
    client = OpenSimClient('http://example.com', 'user', 'pass', 'First', 'Last')

    class Resp:
        def __init__(self, data):
            self._data = data

        def raise_for_status(self):
            pass

        def json(self):
            return self._data

    login_data = {
        'session_id': 'sess',
        'agent_id': 'agent',
        'seed_capability': 'seed',
        'event_queue': 'http://example.com/ev',
        'movement': 'http://example.com/move',
    }

    monkeypatch.setattr('pyopensim.client.requests.post', lambda *a, **k: Resp(login_data))
    monkeypatch.setattr('pyopensim.client.requests.get', lambda *a, **k: Resp({'events': []}))

    called = {}

    def fake_thread(*args, **kwargs):
        called['start'] = True
        class T:
            def start(self):
                pass
            def is_alive(self):
                return False
            def join(self, timeout=None):
                pass
        return T()

    monkeypatch.setattr('pyopensim.client.threading.Thread', fake_thread)

    assert client.login()
    assert client.session_id == 'sess'
    assert client.event_queue_cap == 'http://example.com/ev'
    assert called.get('start')
