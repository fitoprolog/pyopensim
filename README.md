# PyOpenSim

PyOpenSim is an experimental Python client skeleton for connecting to
[OpenSimulator](https://opensimulator.org/) grids. The goal of the project is to
provide a starting point for programmatic interactions with SecondLife/OpenSim
worlds from Python.

**Current Status**: PyOpenSim is still highly experimental. It implements a
very small subset of the SecondLife/OpenSim protocols but demonstrates how a
client might log in, poll the event queue and display placeholder objects using
`pyglet`.

## Features

- Connect to a grid and start polling the event queue.
- Minimal 3D rendering window using `pyglet` that draws cubes for objects.
- Simple avatar actions using capabilities.
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
    renderer = Renderer(client.scene)
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
