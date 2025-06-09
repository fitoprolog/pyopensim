# Basic package metadata.

__version__ = "0.1.0"

# The auto-generated port contains many modules with syntax errors.  Importing
# them in ``__init__`` would raise exceptions during test collection.  Only the
# minimal ``basic`` submodule is exported here so unit tests can import the
# simplified implementation without pulling in the broken code.

__all__ = ["basic", "__version__"]
