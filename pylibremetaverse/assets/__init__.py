# __init__.py for pylibremetaverse.assets
# This file marks the directory as a Python package.

from .asset_base import Asset
from .asset_notecard import AssetNotecard
from .asset_landmark import AssetLandmark
# from .asset_texture import AssetTexture # Example for future
# from .asset_sound import AssetSound     # Example for future
# ... etc.

__all__ = [
    "Asset",
    "AssetNotecard",
    "AssetLandmark",
    # "AssetTexture",
    # "AssetSound",
]
