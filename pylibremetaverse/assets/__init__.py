# __init__.py for pylibremetaverse.assets
# This file marks the directory as a Python package.

from .asset_base import Asset
from .asset_notecard import AssetNotecard
from .asset_landmark import AssetLandmark
from .asset_texture import AssetTexture
from .asset_wearable import AssetWearable
# ... etc.

__all__ = [
    "Asset",
    "AssetNotecard",
    "AssetLandmark",
    "AssetTexture",
    "AssetWearable",
]
