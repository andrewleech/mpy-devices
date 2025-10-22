"""MicroPython device checker and monitor."""

__version__ = "1.0.0"

from .core import (
    DeviceError,
    DeviceInfo,
    DeviceNotFoundError,
    MicroPythonVersion,
    ParseError,
    QueryTimeoutError,
    discover_devices,
    find_device,
    query_device,
    resolve_shortcut,
)

__all__ = [
    "DeviceInfo",
    "MicroPythonVersion",
    "DeviceError",
    "DeviceNotFoundError",
    "QueryTimeoutError",
    "ParseError",
    "discover_devices",
    "query_device",
    "find_device",
    "resolve_shortcut",
]
