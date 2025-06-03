from pyopensim.packets import PacketType

def test_enum_contains_known_values():
    assert PacketType.TeleportRequest == 65598
    assert PacketType.ObjectAnimation == 196638
    assert len(list(PacketType)) > 300
