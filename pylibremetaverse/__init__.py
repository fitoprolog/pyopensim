# This file marks pylibremetaverse as a Python package.

from .client import GridClient
from . import types
from . import utils
from . import managers # If users need direct access to manager types, otherwise optional
from . import network # If users need direct access to network components, otherwise optional

__version__ = "0.1.0" # Example version

__all__ = [
    "GridClient",
    "types",
    "utils",
    "managers",
    "network",
    "__version__",
]
