# PyOpenSim

PyOpenSim is an experimental Python client skeleton for connecting to
[OpenSimulator](https://opensimulator.org/) grids. The goal of the project is to
provide a starting point for programmatic interactions with SecondLife/OpenSim
worlds from Python.

**Current Status**: This repository contains only minimal scaffolding and does
not implement the full SecondLife protocol or 3D rendering. It simply outlines a
possible architecture for such a client. Contributions are welcome!

## Features

- Connect to a grid using a placeholder login request.
- Minimal 3D rendering window using `pyglet` (no real asset support yet).
- Example stubs for avatar actions.
- Packet type enumeration generated from LibreMetaverse.

## Usage

Install dependencies:

```bash
pip install requests pyglet
```

Example code:

```python
from pyopensim import OpenSimClient, Renderer

client = OpenSimClient(
    login_uri="http://example.com/login",
    username="myuser",
    password="mypass",
    first="First",
    last="Last",
)

if client.login():
    print("Logged in!")
    renderer = Renderer()
    renderer.start()
```

This example will open a window using `pyglet` but will not display any
in-world content.

### Updating Packet Definitions

Packet definitions in `pyopensim/packets.py` are generated from the
LibreMetaverse project. To refresh them, run:

```bash
python scripts/update_packets.py
```

## Disclaimer

This project is in a very early stage and does not yet implement the complex
protocols required for a full OpenSimulator or SecondLife viewer. Use at your
own risk.
