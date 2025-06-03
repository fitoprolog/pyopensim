from pyopensim.client import OpenSimClient


def test_client_initial_state():
    client = OpenSimClient('http://example.com', 'user', 'pass', 'First', 'Last')
    assert not client.is_connected()
