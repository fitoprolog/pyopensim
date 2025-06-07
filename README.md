# PyLibreMetaverse

## Introduction

PyLibreMetaverse is a Python client library for interacting with Second Life and OpenSimulator virtual worlds. It is a port of concepts and structures from the well-regarded C# [LibreMetaverse](https://github.com/LibreMetaverse/LibreMetaverse) library.

**Current Status:** This project is currently in an **experimental/alpha stage**. While many foundational features are implemented, it is not yet a complete client and should be used with an understanding of its limitations.

## Features

PyLibreMetaverse currently supports the following key features:

*   **Login & Session Management:**
    *   Full login sequence via LLSD.
    *   UDP circuit establishment and keep-alive.
    *   Packet reliability layer (ACKS, resends).
    *   Graceful logout.
*   **Core Data Types:**
    *   CustomUUID, Vector2, Vector3, Vector3d, Vector4, Quaternion, Matrix4, Color4.
    *   Various enums for packet types, asset types, inventory types, etc.
*   **Packet Handling:**
    *   Infrastructure for serializing and deserializing network packets.
    *   Packet factory for constructing packet objects from incoming data.
*   **AgentManager (`client.self`)**:
    *   Movement: Walking, running, flying, turning, jumping, crouching.
    *   Camera controls.
    *   Chat: Sending and receiving local chat.
    *   Instant Messages (IMs): Sending and receiving.
    *   Teleportation: To landmarks, specific locations, home, and responding to teleport lures.
    *   Animations: Playing and stopping basic system animations.
    *   Gestures: Activating and deactivating gestures (requires gesture asset in inventory).
    *   Script Dialogs: Receiving and responding to dialogs from in-world objects.
    *   Script Permissions: Responding to permission requests.
    *   Mute List: Requesting and parsing the agent's mute list (requires Xfer asset download).
*   **ObjectManager (`client.objects`)**:
    *   Tracking objects in view (Prims and Avatars).
    *   Parsing `ObjectUpdate` (full) and `ImprovedTerseObjectUpdate` packets for position, rotation, velocity, acceleration, and angular velocity.
    *   Requesting and parsing object properties (`ObjectPropertiesFamilyPacket`, `ObjectPropertiesPacket`).
    *   Object selection and de-selection.
    *   Object linking and de-linking.
    *   Basic object manipulation: Move, Scale, Rotate.
    *   Object creation (rezzing) via `ObjectAddPacket`.
    *   Setting object Name, Description, Text (hover text), and ClickAction.
*   **AppearanceManager (`client.appearance`)**:
    *   Fetching current agent wearables and visual parameters (`AgentWearablesUpdatePacket`).
    *   Sending `AgentSetAppearancePacket` to change appearance (relies on server-side baking for wearables).
    *   Receiving `AvatarAppearancePacket` to update agent's own TextureEntry and visual parameters.
*   **InventoryManager (`client.inventory`)**:
    *   Fetching inventory skeleton (root folders) at login.
    *   Recursively fetching the contents of inventory folders via CAPS.
    *   Creating new inventory folders.
    *   Moving inventory items and folders between folders.
    *   Copying inventory items.
    *   Moving items/folders to the Trash folder.
    *   Purging items/folders from the Trash folder.
*   **AssetManager (`client.assets`)**:
    *   Xfer system for asset downloads (currently used for Mute List).
    *   Texture downloading via "GetTexture" CAPS.
    *   UDP texture download fallback (basic implementation for `RequestImage`, `ImageData`, `ImageNotInDatabase`).
    *   Parsing for `AssetNotecard` (Linden Text Format) and `AssetLandmark` (SLALM format) from downloaded asset data.
    *   Base `Asset` class for other asset types (stores raw data).

## Setup and Installation

1.  **Python Version:** Python 3.9 or higher is recommended.
2.  **Dependencies:** The primary external dependency is `httpx` for HTTP CAPS communication.
    ```bash
    pip install httpx
    ```
3.  **Installation:**
    *   Clone this repository:
        ```bash
        git clone <repository_url>
        cd pylibremetaverse
        ```
    *   It's recommended to use a virtual environment:
        ```bash
        python -m venv venv
        source venv/bin/activate  # On Windows: venv\Scripts\activate
        ```
    *   Install dependencies (if a `requirements.txt` is provided, or just `httpx` for now):
        ```bash
        pip install httpx
        ```
    *   The library can be used by adding its path to your `PYTHONPATH` or by installing it as a package (e.g., via `pip install .` if `setup.py` is configured).

## Usage

The primary way to interact with the library is through the `GridClient` class. The `examples/python_test_client.py` script provides a comprehensive example of its usage.

**Running the Example Test Client:**

1.  Navigate to the `examples` directory.
2.  Set the following environment variables for your bot's credentials:
    *   `PYLIBREMV_FIRSTNAME`: Your bot's first name.
    *   `PYLIBREMV_LASTNAME`: Your bot's last name.
    *   `PYLIBREMV_PASSWORD`: Your bot's password.
    *   `PYLIBREMV_LOGINURI` (Optional): The login URI for the grid. Defaults to the Second Life Agni grid. For OpenSimulator grids, this will be different (e.g., `http://yourgrid.com:8002/`).
3.  Run the script:
    ```bash
    python python_test_client.py
    ```
    The client will log its actions to the console.

**Conceptual Code Snippet:**

```python
import asyncio
import logging
from pylibremetaverse.client import GridClient
from pylibremetaverse.types.enums import ChatType

# Configure logging
logging.basicConfig(level=logging.INFO)

async def main():
    client = GridClient()

    # Register event handlers (examples)
    def on_chat(chat_args):
        logging.info(f"Chat from {chat_args.from_name}: {chat_args.message}")

    client.self.register_chat_handler(on_chat)

    # Login (replace with your actual credentials or use environment variables)
    login_uri = "LOGIN_URI_HERE" # e.g., client.settings.AGNI_LOGIN_SERVER
    first_name = "YourBotFirstName"
    last_name = "YourBotLastName"
    password = "YourBotPassword"

    if await client.network.login(first_name, last_name, password, "PyLibreMV Test", "1.0.0", "last", login_uri):
        logging.info("Login successful!")

        # Wait for sim connection and handshake
        await client.network.wait_for_sim_connection() # Helper that might need to be implemented in client or used via events

        if client.network.current_sim and client.network.current_sim.handshake_complete:
            # Example action: Send a chat message
            await client.self.chat("Hello from PyLibreMetaverse!", channel=0, chat_type=ChatType.NORMAL)

            # Let the client run for a bit
            await asyncio.sleep(30)
        else:
            logging.error("Sim connection or handshake failed.")

        await client.network.logout()
    else:
        logging.error(f"Login failed: {client.network.login_message}")

if __name__ == "__main__":
    asyncio.run(main())
```
**Note:** The snippet above is conceptual. Refer to `examples/python_test_client.py` for a runnable and more feature-complete example.

## Current Limitations

*   **Experimental Software:** The library is still under active development and may have bugs or incomplete features. APIs might change.
*   **Incomplete Object Parsing:** While basic object tracking and some properties are handled, full parsing of all `ObjectUpdate` fields (especially complex ones like TextureEntry for all prim types, light/particle params, flexible object params) is not yet complete. Terse object update decoding is partial.
*   **No Client-Side Baking:** Appearance changes rely on server-side baking. The library does not currently generate or modify `TextureEntry` bakes on the client.
*   **Partial Packet/CAPS Coverage:** Many packet types and CAPS services are not yet implemented.
*   **Asset Handling:** While basic texture, notecard, and landmark asset downloading and parsing are implemented, many other asset types and more robust parsing are needed. UDP asset transfer is only partially stubbed for textures.

## Disclaimer

This software is experimental and provided "as is", without warranty of any kind, express or implied. Use at your own risk. It is not an official client from Linden Lab or any grid operator. Ensure your use complies with the Terms of Service of any grid you connect to.
