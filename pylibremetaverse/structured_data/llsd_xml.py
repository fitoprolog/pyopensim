import xml.etree.ElementTree as ET
import base64
import datetime
import logging

from .osd import (
    OSD, OSDType, OSDBoolean, OSDInteger, OSDReal, OSDString,
    OSDUUID, OSDDate, OSDUri, OSDBinary, OSDMap, OSDArray,
    python_to_osd # Helper for convenience
)
from pylibremetaverse.types import CustomUUID

logger = logging.getLogger(__name__)

def _parse_xml_node(node: ET.Element) -> OSD:
    """Helper function to parse an individual XML element into an OSD object."""
    tag = node.tag.lower() # Normalize tag name

    if tag == 'map':
        osd_map = OSDMap()
        key_element = None
        for child in node:
            if child.tag.lower() == 'key':
                key_element = child.text.strip() if child.text else ""
            else:
                if key_element is None:
                    logger.warning("LLSD XML map parsing: value found before key. Skipping.")
                    continue # Should have a key first
                osd_map[key_element] = _parse_xml_node(child)
                key_element = None # Reset key for next pair
        return osd_map

    elif tag == 'array':
        osd_array = OSDArray()
        for child in node:
            osd_array.append(_parse_xml_node(child))
        return osd_array

    elif tag == 'undef': # <undef /> represents OSDType.UNKNOWN or None
        return OSD() # OSDType.UNKNOWN

    # Handle text content for simple types
    text_content = node.text.strip() if node.text else ""

    if tag == 'boolean':
        return OSDBoolean(text_content == 'true' or text_content == '1')
    elif tag == 'integer' or tag == 'i4' or tag == 'i8': # i4/i8 are alternatives for integer
        return OSDInteger(int(text_content)) if text_content else OSDInteger(0)
    elif tag == 'real' or tag == 'double': # double is an alternative for real
        return OSDReal(float(text_content)) if text_content else OSDReal(0.0)
    elif tag == 'string':
        return OSDString(text_content)
    elif tag == 'uuid':
        return OSDUUID(CustomUUID(text_content)) if text_content else OSDUUID(CustomUUID.ZERO)
    elif tag == 'date':
        # Format: YYYY-MM-DDTHH:MM:SS.FFFFFFZ or YYYY-MM-DDTHH:MM:SSZ
        try:
            if '.' in text_content:
                dt_val = datetime.datetime.strptime(text_content, '%Y-%m-%dT%H:%M:%S.%fZ')
            else:
                dt_val = datetime.datetime.strptime(text_content, '%Y-%m-%dT%H:%M:%SZ')
            return OSDDate(dt_val.replace(tzinfo=datetime.timezone.utc))
        except ValueError:
            logger.warning(f"LLSD XML: Could not parse date '{text_content}'. Using epoch.")
            return OSDDate(0.0) # Epoch
    elif tag == 'uri':
        return OSDUri(text_content)
    elif tag == 'binary':
        # Attributes might indicate encoding, default is base64
        # encoding = node.attrib.get('encoding', 'base64').lower()
        # if encoding != 'base64':
        #     logger.warning(f"LLSD XML: Unsupported binary encoding '{encoding}'. Treating as empty.")
        #     return OSDBinary(b'')
        return OSDBinary(base64.b64decode(text_content)) if text_content else OSDBinary(b'')

    logger.warning(f"LLSD XML: Unknown or unhandled tag type '{tag}'. Treating as OSDType.UNKNOWN.")
    return OSD() # Fallback for unknown tags


def parse_llsd_xml(xml_data: str | bytes) -> OSD:
    """
    Parses an LLSD XML string or bytes into an OSD object hierarchy.

    Args:
        xml_data: The LLSD XML data as a string or bytes.

    Returns:
        An OSD object representing the root of the parsed data.
        Returns OSD(OSDType.UNKNOWN) if parsing fails at the top level.
    """
    if isinstance(xml_data, bytes):
        xml_data = xml_data.decode('utf-8', errors='replace')

    try:
        root = ET.fromstring(xml_data)
    except ET.ParseError as e:
        logger.error(f"LLSD XML parsing failed: {e}. XML data: '{xml_data[:200]}...'")
        return OSD() # Return UNKNOWN OSD on parse error

    if root.tag.lower() != 'llsd':
        logger.warning(f"LLSD XML root tag is not <llsd>, found <{root.tag}>. Attempting to parse children directly.")
        # Some systems might omit the <llsd> wrapper if there's only one child.
        # Or, if the root itself is the data type (e.g. <map>...</map> as root)
        if len(root) == 1: # If the root is not <llsd> but contains one element, parse that element.
             return _parse_xml_node(root[0])
        else: # Otherwise, try to parse the root itself as a data node.
             return _parse_xml_node(root)


    if len(root) == 0: # Empty <llsd />
        return OSD() # Represents OSDType.UNKNOWN or an undefined value
    elif len(root) == 1:
        # The actual data is the child of <llsd>
        return _parse_xml_node(root[0])
    else:
        logger.warning("LLSD XML: <llsd> tag has multiple children. This is unusual. Parsing first child.")
        return _parse_xml_node(root[0])


def _serialize_osd_to_xml_node(osd_data: OSD, parent_element: ET.Element | None = None) -> ET.Element:
    """
    Helper function to serialize an OSD object to an XML element.
    If parent_element is provided, the new element is appended to it.
    Otherwise, a new element is created and returned.
    """
    el: ET.Element

    if osd_data.osd_type == OSDType.MAP:
        el = ET.Element('map')
        assert isinstance(osd_data, OSDMap)
        for key, value_osd in osd_data.items():
            key_el = ET.SubElement(el, 'key')
            key_el.text = str(key) # Keys in OSDMap are always strings
            _serialize_osd_to_xml_node(value_osd, el) # Append value OSD as child of map

    elif osd_data.osd_type == OSDType.ARRAY:
        el = ET.Element('array')
        assert isinstance(osd_data, OSDArray)
        for item_osd in osd_data:
            _serialize_osd_to_xml_node(item_osd, el) # Append item OSD as child of array

    elif osd_data.osd_type == OSDType.BOOLEAN:
        el = ET.Element('boolean')
        el.text = osd_data.as_string()
    elif osd_data.osd_type == OSDType.INTEGER:
        el = ET.Element('integer')
        el.text = osd_data.as_string()
    elif osd_data.osd_type == OSDType.REAL:
        el = ET.Element('real')
        el.text = osd_data.as_string() # Consider C# formatting "r" for round-trip precision
    elif osd_data.osd_type == OSDType.STRING:
        el = ET.Element('string')
        el.text = osd_data.as_string()
    elif osd_data.osd_type == OSDType.UUID:
        el = ET.Element('uuid')
        el.text = osd_data.as_string()
    elif osd_data.osd_type == OSDType.DATE:
        el = ET.Element('date')
        el.text = osd_data.as_string()
    elif osd_data.osd_type == OSDType.URI:
        el = ET.Element('uri')
        el.text = osd_data.as_string()
    elif osd_data.osd_type == OSDType.BINARY:
        el = ET.Element('binary')
        # el.set('encoding', 'base64') # Optional, base64 is default
        el.text = osd_data.as_string() # OSDBinary.as_string() should return base64
    elif osd_data.osd_type == OSDType.UNKNOWN: # Represents <undef />
        el = ET.Element('undef')
    else:
        logger.error(f"LLSD XML Serialization: Cannot serialize OSDType {osd_data.osd_type}")
        # Fallback to <undef /> for unsupported types during serialization
        el = ET.Element('undef')

    if parent_element is not None:
        parent_element.append(el)
    return el


def serialize_llsd_xml(osd_data: OSD, pretty_print: bool = False) -> str:
    """
    Serializes an OSD object hierarchy to an LLSD XML string.

    Args:
        osd_data: The root OSD object to serialize.
        pretty_print: If True, adds indentation and newlines for readability.

    Returns:
        An LLSD XML string representation of the OSD data.
    """
    llsd_root_el = ET.Element('llsd')
    _serialize_osd_to_xml_node(osd_data, llsd_root_el)

    if pretty_print:
        # ET.indent is available in Python 3.9+
        if hasattr(ET, 'indent'):
            ET.indent(llsd_root_el)
        else:
            # Manual pretty printing (basic) for older Python versions
            # This is a simplified version, a more robust one would use xml.dom.minidom
            pass # For now, no pretty print on older Python if ET.indent not found

    # ET.tostring returns bytes, so decode to string
    return ET.tostring(llsd_root_el, encoding='unicode') # encoding='unicode' gives str
