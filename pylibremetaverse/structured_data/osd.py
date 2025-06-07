import enum
import datetime
import uuid # Standard Python UUID
from pylibremetaverse.types import CustomUUID # Your custom UUID, if different behaviorally

class OSDType(enum.Enum):
    UNKNOWN = 0
    BOOLEAN = 1
    INTEGER = 2
    REAL = 3
    STRING = 4
    UUID = 5 # Will use CustomUUID
    DATE = 6
    URI = 7
    BINARY = 8
    MAP = 9
    ARRAY = 10

class OSD:
    """Base class for OSD (Object Structured Data) elements."""
    def __init__(self, type: OSDType = OSDType.UNKNOWN):
        self.osd_type: OSDType = type # Renamed to avoid conflict with Python's type()

    def as_boolean(self) -> bool:
        raise TypeError(f"Cannot convert OSDType {self.osd_type} to Boolean")

    def as_integer(self) -> int:
        raise TypeError(f"Cannot convert OSDType {self.osd_type} to Integer")

    def as_real(self) -> float:
        raise TypeError(f"Cannot convert OSDType {self.osd_type} to Real")

    def as_string(self) -> str:
        raise TypeError(f"Cannot convert OSDType {self.osd_type} to String")

    def as_uuid(self) -> CustomUUID:
        raise TypeError(f"Cannot convert OSDType {self.osd_type} to UUID")

    def as_date(self) -> datetime.datetime:
        raise TypeError(f"Cannot convert OSDType {self.osd_type} to Date")

    def as_uri(self) -> str: # Or a more specific URI type if you have one
        raise TypeError(f"Cannot convert OSDType {self.osd_type} to URI")

    def as_binary(self) -> bytes:
        raise TypeError(f"Cannot convert OSDType {self.osd_type} to Binary")

    def as_python_object(self):
        """Converts the OSD element to a native Python object."""
        if self.osd_type == OSDType.BOOLEAN: return self.as_boolean()
        if self.osd_type == OSDType.INTEGER: return self.as_integer()
        if self.osd_type == OSDType.REAL: return self.as_real()
        if self.osd_type == OSDType.STRING: return self.as_string()
        if self.osd_type == OSDType.UUID: return self.as_uuid() # or str(self.as_uuid()) if needed
        if self.osd_type == OSDType.DATE: return self.as_date()
        if self.osd_type == OSDType.URI: return self.as_uri()
        if self.osd_type == OSDType.BINARY: return self.as_binary()
        # For MAP and ARRAY, this will be overridden in their respective classes.
        raise TypeError(f"Cannot convert OSDType {self.osd_type} to a simple Python object directly.")


    def __str__(self) -> str:
        return f"OSD(Type: {self.osd_type})"

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} type={self.osd_type}>"

class OSDBoolean(OSD):
    def __init__(self, value: bool):
        super().__init__(OSDType.BOOLEAN)
        self.value: bool = bool(value) # Ensure it's a bool

    def as_boolean(self) -> bool: return self.value
    def as_string(self) -> str: return "true" if self.value else "false"
    def __str__(self) -> str: return self.as_string()
    def __repr__(self) -> str: return f"OSDBoolean({self.value})"
    def __eq__(self, other): return isinstance(other, OSDBoolean) and self.value == other.value

class OSDInteger(OSD):
    def __init__(self, value: int):
        super().__init__(OSDType.INTEGER)
        self.value: int = int(value) # Ensure it's an int

    def as_integer(self) -> int: return self.value
    def as_real(self) -> float: return float(self.value)
    def as_string(self) -> str: return str(self.value)
    def __str__(self) -> str: return self.as_string()
    def __repr__(self) -> str: return f"OSDInteger({self.value})"
    def __eq__(self, other): return isinstance(other, OSDInteger) and self.value == other.value

class OSDReal(OSD):
    def __init__(self, value: float):
        super().__init__(OSDType.REAL)
        self.value: float = float(value) # Ensure it's a float

    def as_integer(self) -> int: return int(self.value)
    def as_real(self) -> float: return self.value
    def as_string(self) -> str: return str(self.value) # Consider formatting like C# (e.g., "r", "g")
    def __str__(self) -> str: return self.as_string()
    def __repr__(self) -> str: return f"OSDReal({self.value})"
    def __eq__(self, other): return isinstance(other, OSDReal) and self.value == other.value


class OSDString(OSD):
    def __init__(self, value: str):
        super().__init__(OSDType.STRING)
        self.value: str = str(value)

    def as_string(self) -> str: return self.value
    def __str__(self) -> str: return self.value
    def __repr__(self) -> str: return f"OSDString('{self.value}')"
    def __eq__(self, other): return isinstance(other, OSDString) and self.value == other.value

class OSDUUID(OSD):
    def __init__(self, value: CustomUUID | uuid.UUID | str | None):
        super().__init__(OSDType.UUID)
        if isinstance(value, CustomUUID):
            self.value: CustomUUID = value
        elif isinstance(value, uuid.UUID):
            self.value: CustomUUID = CustomUUID(str(value)) # Convert standard UUID to CustomUUID
        elif isinstance(value, str):
            self.value: CustomUUID = CustomUUID(value)
        elif value is None: # Represent null UUID
            self.value: CustomUUID = CustomUUID.ZERO # Assuming CustomUUID has a ZERO equivalent
        else:
            raise TypeError(f"Invalid type for OSDUUID value: {type(value)}")

    def as_uuid(self) -> CustomUUID: return self.value
    def as_string(self) -> str: return str(self.value)
    def __str__(self) -> str: return self.as_string()
    def __repr__(self) -> str: return f"OSDUUID('{self.value}')"
    def __eq__(self, other): return isinstance(other, OSDUUID) and self.value == other.value

class OSDDate(OSD):
    _EPOCH_DATETIME = datetime.datetime(1970, 1, 1, tzinfo=datetime.timezone.utc)

    def __init__(self, value: datetime.datetime | float): # float is seconds since epoch
        super().__init__(OSDType.DATE)
        if isinstance(value, datetime.datetime):
            self.value: datetime.datetime = value
        elif isinstance(value, (int, float)):
            # Ensure timestamp is positive, as C# LLSD does not handle negative dates well
            if value < 0: value = 0
            self.value = self._EPOCH_DATETIME + datetime.timedelta(seconds=value)
        else:
            raise TypeError("OSDDate value must be a datetime object or POSIX timestamp.")

    def as_date(self) -> datetime.datetime: return self.value
    def as_string(self) -> str: # ISO 8601 format
        return self.value.strftime('%Y-%m-%dT%H:%M:%S.%fZ')
    def as_unix_time(self) -> float:
        return (self.value - self._EPOCH_DATETIME).total_seconds()
    def __str__(self) -> str: return self.as_string()
    def __repr__(self) -> str: return f"OSDDate('{self.as_string()}')"
    def __eq__(self, other): return isinstance(other, OSDDate) and self.value == other.value

class OSDUri(OSD):
    def __init__(self, value: str): # Consider using a URL parsing library for validation
        super().__init__(OSDType.URI)
        self.value: str = str(value)

    def as_uri(self) -> str: return self.value
    def as_string(self) -> str: return self.value
    def __str__(self) -> str: return self.as_string()
    def __repr__(self) -> str: return f"OSDUri('{self.value}')"
    def __eq__(self, other): return isinstance(other, OSDUri) and self.value == other.value

class OSDBinary(OSD):
    def __init__(self, value: bytes):
        super().__init__(OSDType.BINARY)
        if not isinstance(value, bytes):
            raise TypeError("OSDBinary value must be bytes.")
        self.value: bytes = value

    def as_binary(self) -> bytes: return self.value
    def as_string(self) -> str: # Base64 encode
        import base64
        return base64.b64encode(self.value).decode('ascii')
    def __str__(self) -> str: return self.as_string() # Or a more readable representation
    def __repr__(self) -> str: return f"OSDBinary(len={len(self.value)})"
    def __eq__(self, other): return isinstance(other, OSDBinary) and self.value == other.value

class OSDMap(OSD, dict):
    def __init__(self, initial_dict: dict | None = None):
        OSD.__init__(self, OSDType.MAP)
        dict.__init__(self)
        if initial_dict:
            for key, value in initial_dict.items():
                if not isinstance(key, str):
                    raise TypeError("OSDMap keys must be strings.")
                if not isinstance(value, OSD): # Ensure values are OSD objects
                    # Attempt to convert basic python types to OSD types
                    self[key] = python_to_osd(value)
                else:
                    self[key] = value

    def as_python_object(self) -> dict:
        """Converts the OSDMap to a native Python dictionary."""
        py_dict = {}
        for key, value in self.items():
            if isinstance(value, (OSDMap, OSDArray)):
                py_dict[key] = value.as_python_object()
            elif isinstance(value, OSD):
                py_dict[key] = value.as_python_object() # Use the OSD's own converter
            else: # Should not happen if map contains only OSD objects
                py_dict[key] = value
        return py_dict

    def __str__(self) -> str:
        return repr(self.as_python_object()) # More readable than default dict str
    def __repr__(self) -> str: return f"OSDMap({len(self)} items)"

class OSDArray(OSD, list):
    def __init__(self, initial_list: list | None = None):
        OSD.__init__(self, OSDType.ARRAY)
        list.__init__(self)
        if initial_list:
            for item in initial_list:
                if not isinstance(item, OSD): # Ensure items are OSD objects
                    self.append(python_to_osd(item))
                else:
                    self.append(item)

    def as_python_object(self) -> list:
        """Converts the OSDArray to a native Python list."""
        py_list = []
        for item in self:
            if isinstance(item, (OSDMap, OSDArray)):
                py_list.append(item.as_python_object())
            elif isinstance(item, OSD):
                py_list.append(item.as_python_object()) # Use the OSD's own converter
            else: # Should not happen
                py_list.append(item)
        return py_list

    def __str__(self) -> str:
        return repr(self.as_python_object())
    def __repr__(self) -> str: return f"OSDArray({len(self)} items)"

# Helper function to convert Python types to OSD types (used by OSDMap/OSDArray constructors)
def python_to_osd(data) -> OSD:
    """Converts a Python native type to its OSD equivalent."""
    if isinstance(data, OSD): return data
    if isinstance(data, bool): return OSDBoolean(data)
    if isinstance(data, int): return OSDInteger(data)
    if isinstance(data, float): return OSDReal(data)
    if isinstance(data, str): return OSDString(data) # Could be OSDUri if it matches URI pattern
    if isinstance(data, CustomUUID): return OSDUUID(data)
    if isinstance(data, uuid.UUID): return OSDUUID(CustomUUID(str(data)))
    if isinstance(data, datetime.datetime): return OSDDate(data)
    if isinstance(data, bytes): return OSDBinary(data)
    if isinstance(data, dict):
        return OSDMap({k: python_to_osd(v) for k, v in data.items()})
    if isinstance(data, list):
        return OSDArray([python_to_osd(item) for item in data])
    if data is None: # Representing <undef /> in LLSD
        return OSD() # OSDType.UNKNOWN
    raise TypeError(f"Cannot automatically convert Python type {type(data)} to OSD.")
