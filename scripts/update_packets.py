#!/usr/bin/env python
"""Generate PacketType enum from LibreMetaverse _Packets_.cs"""
import re
import requests

URL = "https://raw.githubusercontent.com/cinderblocks/libremetaverse/master/LibreMetaverse/_Packets_.cs"


def fetch_packets(url=URL):
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    return resp.text


def parse_enum(text: str):
    enum_pattern = re.compile(r"enum PacketType(.*?)\n\s*}\s*$", re.S | re.M)
    m = enum_pattern.search(text)
    if not m:
        raise RuntimeError("PacketType enum not found")
    body = m.group(1)
    entries = []
    current = -1
    for line in body.splitlines():
        line = line.strip()
        if not line or line.startswith("//") or line.startswith("///"):
            continue
        m_val = re.match(r"([A-Za-z0-9_]+)\s*=\s*(\d+),?", line)
        if m_val:
            name, val = m_val.groups()
            current = int(val)
        else:
            m_name = re.match(r"([A-Za-z0-9_]+),?", line)
            if not m_name:
                continue
            name = m_name.group(1)
            current += 1
        entries.append((name, current))
    return entries


def generate(entries):
    lines = ["from enum import IntEnum", "", "class PacketType(IntEnum):"]
    for name, val in entries:
        lines.append(f"    {name} = {val}")
    lines.append("")
    return "\n".join(lines)


def main():
    text = fetch_packets()
    entries = parse_enum(text)
    with open("pyopensim/packets.py", "w", encoding="utf-8") as f:
        f.write(generate(entries))
    print(f"Generated {len(entries)} PacketType entries")


if __name__ == "__main__":
    main()
