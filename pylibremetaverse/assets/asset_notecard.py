import dataclasses
import re
from .asset_base import Asset
from pylibremetaverse.types import AssetType # For setting default asset_type

@dataclasses.dataclass
class AssetNotecard(Asset):
    """Represents a notecard asset."""
    body_text: str = ""
    # Linden Text Format can include embedded assets, permissions, etc.
    # For now, focusing on the main body text.
    # Example: "Linden Text Format version 1.0\n{\nLLEmbeddedItems version 1.0\n{\ncount 0\n}\nText length NNNN\n...body_text...}"

    def __post_init__(self):
        super().__post_init__() # Ensure base class __post_init__ is called
        if self.asset_type == AssetType.Unknown: # Default if not set by creator
            self.asset_type = AssetType.Notecard

    def from_bytes(self, data: bytes) -> bool:
        """
        Parses notecard data from its raw byte representation.
        Assumes "Linden Text Format" (LTF).
        """
        super().from_bytes(data) # Stores raw_data
        self.loaded_successfully = False # Assume failure until parsing succeeds

        try:
            text_content = data.decode('utf-8')

            # Basic LTF parsing:
            # Look for "Text length NNNN\n...body..."
            # More robust parsing would check version and LLEmbeddedItems.

            # Example simplified parsing for "Text length NNNN\n...body..."
            # This regex tries to find the "Text length" line and capture everything after it.
            # It also handles potential "{ }" blocks for embedded items or metadata.

            # Try to find the start of the actual text body
            # Common pattern: "Text length DDDD\nActual text starts here..."
            match = re.search(r"Text length\s+\d+\s*\n([\s\S]*)", text_content, re.IGNORECASE)
            if match:
                self.body_text = match.group(1).strip()
                self.loaded_successfully = True
            elif "Linden Text Format" in text_content: # It's LTF, but format is unexpected or simpler
                 # Fallback: try to extract text after the initial declaration lines if any
                lines = text_content.splitlines()
                body_start_line = 0
                for i, line in enumerate(lines):
                    if "{" in line and body_start_line == 0 : # Often signifies start of metadata block
                        pass
                    if "}" in line : # Often signifies end of metadata block
                        body_start_line = i + 1
                        continue # continue to check for "Text length"
                    if line.lower().startswith("text length"):
                        body_start_line = i + 1
                        break

                if body_start_line < len(lines):
                    self.body_text = "\n".join(lines[body_start_line:]).strip()
                    self.loaded_successfully = True
                else: # If no clear "Text length" or structure, treat whole content as body after header
                    if lines and lines[0].lower().startswith("linden text format"):
                         self.body_text = "\n".join(lines[1:]).strip() # Skip first line
                         self.loaded_successfully = True # Assume it's valid if it declared LTF
                    else: # Not a recognized LTF, but still text
                         self.body_text = text_content
                         self.loaded_successfully = True # Treat as plain text
            else:
                # Not LTF, treat as plain text
                self.body_text = text_content
                self.loaded_successfully = True # Assume success for plain text

        except UnicodeDecodeError:
            # Try other encodings if UTF-8 fails, or handle as error
            try:
                self.body_text = data.decode('latin-1') # Common fallback
                self.loaded_successfully = True
            except UnicodeDecodeError:
                self.body_text = "Error decoding notecard data."
                # self.raw_data still holds the original bytes
                # self.loaded_successfully remains False (or set explicitly)
                self.loaded_successfully = False

        return self.loaded_successfully

    def __str__(self):
        return f"{super().__str__()} BodyPreview='{self.body_text[:50].replace(chr(10), ' ') + ('...' if len(self.body_text) > 50 else '')}'"
