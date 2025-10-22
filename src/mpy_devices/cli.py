"""Command-line interface for mpy-devices."""

import json
import sys
from typing import Optional

import click
from rich.console import Console
from rich.table import Table

from . import core


console = Console()


def print_device_info(device: core.DeviceInfo, show_header: bool = True):
    """Print device information in text format."""
    if show_header:
        console.print(f"[blue]Querying: {device.path}[/blue]")

    console.print(f"  TTY Path:    {device.path}")

    if device.by_id_path:
        console.print(f"  By-ID Path:  {device.by_id_path}")
    else:
        console.print("  By-ID Path:  [yellow](not found)[/yellow]")

    if device.vid_pid_str:
        console.print(f"  VID:PID:     {device.vid_pid_str}")

    if device.serial_number:
        console.print(f"  Device ID:   {device.serial_number}")


def print_version_info(version: core.MicroPythonVersion):
    """Print MicroPython version information."""
    console.print(f"  Machine:     {version.machine}")
    console.print(f"  System:      {version.sysname}")
    console.print(f"  Release:     {version.release}")
    console.print(f"  Version:     {version.version}")
    console.print()


def check_single_device(device_path: str, timeout: int, verbose: bool) -> bool:
    """
    Check a single device and print results.

    Returns:
        True if successful, False if failed
    """
    # Find device info
    device = core.find_device(device_path)

    if not device:
        # Device not in list, but might still be accessible
        # Create minimal DeviceInfo
        resolved = core.resolve_shortcut(device_path)
        device = core.DeviceInfo(path=resolved)
        device.by_id_path = core.resolve_by_id_path(resolved)

    print_device_info(device)

    try:
        version = core.query_device(device.path, timeout=timeout)
        print_version_info(version)
        return True

    except core.QueryTimeoutError as e:
        console.print(f"[red]✗ Failed to query MicroPython version[/red]")
        if verbose:
            console.print(f"  Error: {e}")
        console.print()
        return False

    except core.ParseError as e:
        console.print(f"[yellow]⚠ Incomplete MicroPython version data[/yellow]")
        if verbose:
            console.print(f"  Error: {e}")
        console.print()
        return False

    except core.DeviceError as e:
        console.print(f"[red]✗ Failed to query MicroPython version[/red]")
        if verbose:
            console.print(f"  Error: {e}")
        console.print()
        return False


def check_all_devices(timeout: int, verbose: bool) -> int:
    """
    Check all discovered devices.

    Returns:
        Number of failed devices
    """
    devices = core.discover_devices()

    if not devices:
        console.print("[yellow]No MicroPython devices found[/yellow]")
        return 0

    console.print(f"[blue]Found {len(devices)} device(s)[/blue]")
    console.print()

    failed = []
    for device in devices:
        try:
            version = core.query_device(device.path, timeout=timeout)
            print_device_info(device)
            print_version_info(version)

        except (core.DeviceError, core.ParseError, core.QueryTimeoutError) as e:
            failed.append(device.path)
            print_device_info(device)
            console.print(f"[red]✗ Failed to query MicroPython version[/red]")
            if verbose:
                console.print(f"  Error: {e}")
            console.print()

    # Retry failed devices
    if failed:
        console.print(f"[yellow]=== Retrying {len(failed)} failed device(s) ===[/yellow]")
        console.print()

        still_failed = 0
        for device_path in failed:
            device = core.find_device(device_path)
            if not device:
                continue

            try:
                version = core.query_device(device.path, timeout=timeout)
                print_device_info(device)
                print_version_info(version)

            except (core.DeviceError, core.ParseError, core.QueryTimeoutError) as e:
                still_failed += 1
                print_device_info(device)
                console.print(f"[red]✗ Failed to query MicroPython version[/red]")
                if verbose:
                    console.print(f"  Error: {e}")
                console.print()

        if still_failed > 0:
            console.print(f"[red]{still_failed} device(s) still failed after retry[/red]")
        else:
            console.print(f"[green]All devices succeeded on retry[/green]")
        console.print()

        return still_failed

    return 0


def list_devices_text():
    """List devices in simple text format (like mpremote connect list)."""
    devices = core.discover_devices()

    if not devices:
        console.print("No devices found")
        return

    for device in devices:
        parts = [device.path]

        if device.serial_number:
            parts.append(device.serial_number)

        if device.vid_pid_str:
            parts.append(device.vid_pid_str)

        if device.manufacturer:
            parts.append(device.manufacturer)

        if device.product:
            parts.append(device.product)

        console.print(" ".join(parts))


def list_devices_json():
    """List devices in JSON format."""
    devices = core.discover_devices()

    data = []
    for device in devices:
        data.append({
            "path": device.path,
            "by_id_path": device.by_id_path,
            "serial_number": device.serial_number,
            "vid": device.vid,
            "pid": device.pid,
            "vid_pid": device.vid_pid_str,
            "manufacturer": device.manufacturer,
            "product": device.product,
            "description": device.description,
        })

    print(json.dumps(data, indent=2))


def check_device_json(device_path: str, timeout: int):
    """Check device and output JSON."""
    device = core.find_device(device_path)

    if not device:
        resolved = core.resolve_shortcut(device_path)
        device = core.DeviceInfo(path=resolved)
        device.by_id_path = core.resolve_by_id_path(resolved)

    result = {
        "device": {
            "path": device.path,
            "by_id_path": device.by_id_path,
            "serial_number": device.serial_number,
            "vid": device.vid,
            "pid": device.pid,
            "vid_pid": device.vid_pid_str,
            "manufacturer": device.manufacturer,
            "product": device.product,
        },
        "version": None,
        "error": None,
    }

    try:
        version = core.query_device(device.path, timeout=timeout)
        result["version"] = {
            "sysname": version.sysname,
            "release": version.release,
            "version": version.version,
            "machine": version.machine,
            "nodename": version.nodename,
        }
    except Exception as e:
        result["error"] = str(e)

    print(json.dumps(result, indent=2))


@click.command()
@click.argument("device", required=False)
@click.option("--list", "list_mode", is_flag=True, help="List all devices (text output)")
@click.option("--json", "json_mode", is_flag=True, help="Output in JSON format")
@click.option("-v", "--verbose", is_flag=True, help="Show detailed error messages")
@click.option("-t", "--timeout", default=5, help="Query timeout in seconds (default: 5)")
@click.option("--version", "show_version", is_flag=True, help="Show version and exit")
def main(device: Optional[str], list_mode: bool, json_mode: bool,
         verbose: bool, timeout: int, show_version: bool):
    """
    MicroPython device checker and monitor.

    \b
    Usage:
      mpy-devices                 Launch TUI interface
      mpy-devices /dev/ttyACM0    Check specific device
      mpy-devices a0              Check device using shortcut
      mpy-devices --list          List all devices
      mpy-devices --json          List devices in JSON format
      mpy-devices --json a0       Check device and output JSON

    \b
    Shortcuts:
      a0-a9   -> /dev/ttyACM0-9 (Linux)
      u0-u9   -> /dev/ttyUSB0-9 (Linux)
      c0-c99  -> COM0-99 (Windows)
    """
    if show_version:
        console.print("mpy-devices 0.1.0")
        sys.exit(0)

    # JSON mode
    if json_mode:
        if device:
            check_device_json(device, timeout)
        else:
            list_devices_json()
        return

    # List mode
    if list_mode:
        list_devices_text()
        return

    # Device check mode
    if device:
        success = check_single_device(device, timeout, verbose)
        sys.exit(0 if success else 1)

    # Default: TUI mode
    try:
        from .tui import run_tui
        run_tui(timeout=timeout)
    except KeyboardInterrupt:
        console.print("\nExiting...")
        sys.exit(0)
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        if verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
