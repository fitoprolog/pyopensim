# This file marks pylibremetaverse.structured_data as a Python package.

from .osd import (
    OSD,
    OSDType,
    OSDBoolean,
    OSDInteger,
    OSDReal,
    OSDString,
    OSDUUID,
    OSDDate,
    OSDUri,
    OSDBinary,
    OSDMap,
    OSDArray,
    python_to_osd # Helper function
)

from .llsd_xml import (
    parse_llsd_xml,
    serialize_llsd_xml
)

__all__ = [
    # OSD base and types
    "OSD",
    "OSDType",
    "OSDBoolean",
    "OSDInteger",
    "OSDReal",
    "OSDString",
    "OSDUUID",
    "OSDDate",
    "OSDUri",
    "OSDBinary",
    "OSDMap",
    "OSDArray",
    "python_to_osd",
    # LLSD XML functions
    "parse_llsd_xml",
    "serialize_llsd_xml",
]
