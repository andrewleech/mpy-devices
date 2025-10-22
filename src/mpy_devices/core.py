"""Core functionality for discovering and querying MicroPython devices."""

import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

import serial.tools.list_ports
from mpremote.transport_serial import SerialTransport


# Error classes
class DeviceError(Exception):
    """Base exception for device-related errors."""
    pass


class DeviceNotFoundError(DeviceError):
    """Device not found or not accessible."""
    pass


class QueryTimeoutError(DeviceError):
    """Device query timed out."""
    pass


class ParseError(DeviceError):
    """Failed to parse device response."""
    pass


@dataclass
class DeviceInfo:
    """Information about a discovered device."""
    path: str
    serial_number: Optional[str] = None
    vid: Optional[int] = None
    pid: Optional[int] = None
    manufacturer: Optional[str] = None
    product: Optional[str] = None
    description: Optional[str] = None
    hwid: Optional[str] = None
    by_id_path: Optional[str] = None

    @property
    def vid_pid_str(self) -> Optional[str]:
        """Return VID:PID as formatted string."""
        if self.vid is not None and self.pid is not None:
            return f"{self.vid:04x}:{self.pid:04x}"
        return None


@dataclass
class MicroPythonVersion:
    """MicroPython version information from os.uname()."""
    sysname: str
    release: str
    version: str
    machine: str
    nodename: Optional[str] = None

    def is_complete(self) -> bool:
        """Check if all required fields were parsed successfully."""
        return all([
            self.sysname and self.sysname != "unknown",
            self.release and self.release != "unknown",
            self.version and self.version != "unknown",
            self.machine and self.machine != "unknown",
        ])


def resolve_shortcut(device: str) -> str:
    """
    Resolve mpremote shortcuts to full device paths.

    Args:
        device: Device path or shortcut (a0, u0, c3, etc.)

    Returns:
        Resolved device path
    """
    # Check for shortcut patterns
    if match := re.match(r"^a(\d+)$", device):
        # Linux/macOS ACM devices
        if sys.platform == "darwin":
            return f"/dev/cu.usbmodem{match.group(1)}"
        else:
            return f"/dev/ttyACM{match.group(1)}"
    elif match := re.match(r"^u(\d+)$", device):
        # Linux/macOS USB-serial devices
        if sys.platform == "darwin":
            return f"/dev/cu.usbserial-{match.group(1)}"
        else:
            return f"/dev/ttyUSB{match.group(1)}"
    elif match := re.match(r"^c(\d+)$", device):
        # Windows COM ports
        return f"COM{match.group(1)}"

    return device


def resolve_by_id_path(device_path: str) -> Optional[str]:
    """
    Find stable /dev/serial/by-id/ path for a device.

    Linux-only feature - returns None on other platforms.

    Args:
        device_path: Device path like /dev/ttyACM0

    Returns:
        Stable by-id path or None if not found
    """
    # by-id paths are Linux-specific
    if sys.platform != "linux":
        return None

    by_id_dir = Path("/dev/serial/by-id")

    if not by_id_dir.exists():
        return None

    try:
        for id_path in by_id_dir.iterdir():
            if id_path.is_symlink():
                target = id_path.resolve()
                if str(target) == device_path:
                    return str(id_path)
    except (OSError, PermissionError):
        pass

    return None


def discover_devices(include_ttyS: bool = False) -> List[DeviceInfo]:  # noqa: N803
    """
    Discover all connected serial devices.

    Args:
        include_ttyS: If True, include /dev/ttyS* devices (usually non-USB, Linux only)

    Returns:
        List of DeviceInfo objects for discovered devices
    """
    devices = []

    for port in sorted(serial.tools.list_ports.comports(), key=lambda p: p.device):
        # Platform-specific filtering of non-USB devices
        if not include_ttyS:
            # Linux: Skip /dev/ttyS* (built-in serial ports)
            if sys.platform == "linux" and port.device.startswith("/dev/ttyS"):
                continue
            # macOS: Skip /dev/tty.* (keep only /dev/cu.*)
            elif sys.platform == "darwin" and port.device.startswith("/dev/tty."):
                continue

        # Build DeviceInfo
        device_info = DeviceInfo(
            path=port.device,
            serial_number=port.serial_number,
            vid=port.vid if isinstance(port.vid, int) else None,
            pid=port.pid if isinstance(port.pid, int) else None,
            manufacturer=port.manufacturer,
            product=port.product,
            description=port.description,
            hwid=port.hwid,
        )

        # Try to resolve by-id path (Linux only)
        device_info.by_id_path = resolve_by_id_path(port.device)

        devices.append(device_info)

    return devices


def query_device(device_path: str, timeout: int = 5) -> MicroPythonVersion:
    """
    Query MicroPython version from a device.

    Args:
        device_path: Path to device (or mpremote shortcut)
        timeout: Query timeout in seconds

    Returns:
        MicroPythonVersion object

    Raises:
        DeviceNotFoundError: Device not accessible
        QueryTimeoutError: Query timed out
        ParseError: Failed to parse response
    """
    import io
    import sys

    # Resolve shortcuts
    resolved_device = resolve_shortcut(device_path)

    # Suppress mpremote's stdout output (it prints b'' in some cases)
    old_stdout = sys.stdout
    sys.stdout = io.StringIO()

    try:
        # Connect to device
        try:
            transport = SerialTransport(resolved_device, baudrate=115200)
        except Exception as e:
            sys.stdout = old_stdout
            raise DeviceNotFoundError(f"Failed to connect to {device_path}: {e}")

        try:
            # Enter raw REPL
            transport.enter_raw_repl(soft_reset=False, timeout_overall=timeout)

            # Query os.uname()
            command = "import os; print(os.uname())"
            output, _ = transport.exec_raw(command, timeout=timeout)
            output_str = output.decode('utf-8', errors='replace').strip()

            # Parse the output
            result = parse_uname_output(output_str)

            # Exit raw REPL and close
            transport.exit_raw_repl()
            transport.close()

            sys.stdout = old_stdout
            return result

        except (TimeoutError, OSError) as e:
            # Timeout errors from mpremote
            try:
                transport.close()
            except Exception:
                pass
            sys.stdout = old_stdout
            raise QueryTimeoutError(f"Query timed out after {timeout}s: {e}")

        except ParseError:
            # Re-raise ParseError as-is
            try:
                transport.close()
            except Exception:
                pass
            sys.stdout = old_stdout
            raise

        except Exception as e:
            # All other errors
            try:
                transport.close()
            except Exception:
                pass
            sys.stdout = old_stdout
            raise DeviceError(f"Failed to query device: {e}")

    finally:
        # Ensure stdout is always restored
        sys.stdout = old_stdout


def parse_uname_output(output: str) -> MicroPythonVersion:
    """
    Parse os.uname() output.

    Expected format:
    (sysname='pyboard', nodename='pyboard', release='1.22.0',
     version='v1.22.0 on 2024-01-01', machine='PYBv1.1 with STM32F405RG')

    Args:
        output: String output from os.uname()

    Returns:
        MicroPythonVersion object

    Raises:
        ParseError: Failed to parse output
    """
    def extract_field(text: str, field: str) -> Optional[str]:
        """Extract a field value from the output."""
        # Handle both single and double quotes
        patterns = [
            rf"{field}='([^']*)'",
            rf'{field}="([^"]*)"',
        ]
        for pattern in patterns:
            if match := re.search(pattern, text):
                return match.group(1)
        return None

    sysname = extract_field(output, "sysname") or "unknown"
    release = extract_field(output, "release") or "unknown"
    version = extract_field(output, "version") or "unknown"
    machine = extract_field(output, "machine") or "unknown"
    nodename = extract_field(output, "nodename")

    result = MicroPythonVersion(
        sysname=sysname,
        release=release,
        version=version,
        machine=machine,
        nodename=nodename,
    )

    if not result.is_complete():
        raise ParseError(
            f"Incomplete version data (one or more fields unknown): {output}"
        )

    return result


def find_device(device_identifier: str) -> Optional[DeviceInfo]:
    """
    Find a device by path, shortcut, or serial number.

    Args:
        device_identifier: Device path, shortcut (a0), or serial number

    Returns:
        DeviceInfo if found, None otherwise
    """
    # Resolve shortcut if applicable
    resolved = resolve_shortcut(device_identifier)

    # Get all devices
    devices = discover_devices(include_ttyS=True)

    # Try exact path match
    for dev in devices:
        if dev.path == resolved or dev.path == device_identifier:
            return dev

    # Try by-id path match
    for dev in devices:
        if dev.by_id_path and dev.by_id_path == device_identifier:
            return dev

    # Try serial number match
    for dev in devices:
        if dev.serial_number and dev.serial_number == device_identifier:
            return dev

    return None
