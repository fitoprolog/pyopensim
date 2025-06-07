import dataclasses
import logging

from .asset_base import Asset
from pylibremetaverse.types import AssetType # For default type

logger = logging.getLogger(__name__)

@dataclasses.dataclass
class AssetScript(Asset):
    """Represents an LSL script asset."""
    script_text: str = ""

    def __post_init__(self):
        super().__post_init__()
        if self.asset_type == AssetType.Unknown: # Default if not set by creator
            self.asset_type = AssetType.LSLText

    def from_bytes(self, data: bytes) -> bool:
        """
        Parses LSL script data from its raw byte representation (UTF-8 text).
        """
        super().from_bytes(data) # Stores raw_data
        try:
            self.script_text = data.decode('utf-8')
            self.loaded_successfully = True
        except UnicodeDecodeError as e:
            logger.error(f"Failed to decode AssetScript {self.asset_id} data as UTF-8: {e}")
            self.script_text = "" # Or keep raw_data as is and mark not loaded successfully
            self.loaded_successfully = False
        return self.loaded_successfully

    def to_upload_bytes(self) -> bytes:
        """
        Returns the LSL script text encoded as UTF-8 bytes for uploading.
        """
        return self.script_text.encode('utf-8')

    def __str__(self):
        return (f"{super().__str__()} ScriptLen={len(self.script_text)} "
                f"Preview='{self.script_text[:50].replace(chr(10), ' ')}...'")

if __name__ == '__main__':
    print("Testing AssetScript...")
    lsl_code = "default { state_entry() { llSay(0, \"Hello, Script!\"); } }"

    # Test creation and to_upload_bytes
    script_asset = AssetScript(name="Test Script", description="A simple test script.", script_text=lsl_code)
    script_asset.asset_type = AssetType.LSLText # Explicitly set

    print(f"Asset: {script_asset}")
    upload_data = script_asset.to_upload_bytes()
    assert upload_data == lsl_code.encode('utf-8')
    print(f"Upload data (first 50 bytes): {upload_data[:50]}")

    # Test from_bytes
    raw_bytes = lsl_code.encode('utf-8')
    script_asset_from_bytes = AssetScript(name="Loaded Script")
    script_asset_from_bytes.asset_type = AssetType.LSLText
    success = script_asset_from_bytes.from_bytes(raw_bytes)

    assert success
    assert script_asset_from_bytes.loaded_successfully
    assert script_asset_from_bytes.script_text == lsl_code
    print(f"Asset from bytes: {script_asset_from_bytes}")

    print("AssetScript tests passed.")
