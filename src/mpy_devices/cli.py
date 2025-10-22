"""Command-line interface for mpy-devices."""

import json
import sys
from typing import Optional

import click
from rich.console import Console

from . import __version__, core

console = Console()


def print_device_info(device: core.DeviceInfo, show_header: bool = True):
    """Print device information in text format."""
    import sys

    if show_header:
        console.print(f"[blue]Querying: {device.path}[/blue]")
        sys.stdout.flush()  # Ensure output appears immediately

    console.print(f"  TTY Path:    {device.path}")

    if device.by_id_path:
        console.print(f"  By-ID Path:  {device.by_id_path}")
    else:
        console.print("  By-ID Path:  [yellow](not found)[/yellow]")

    if device.vid_pid_str:
        console.print(f"  VID:PID:     {device.vid_pid_str}")

    if device.serial_number:
        console.print(f"  Device ID:   {device.serial_number}")

    sys.stdout.flush()  # Ensure output appears immediately


def print_version_info(version: core.MicroPythonVersion):
    """Print MicroPython version information."""
    import sys

    console.print(f"  Machine:     {version.machine}")
    console.print(f"  System:      {version.sysname}")
    console.print(f"  Release:     {version.release}")
    console.print(f"  Version:     {version.version}")
    console.print()
    sys.stdout.flush()  # Ensure output appears immediately


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
        console.print("[red]✗ Failed to query MicroPython version[/red]")
        if verbose:
            console.print(f"  Error: {e}")
        console.print()
        return False

    except core.ParseError as e:
        console.print("[yellow]⚠ Incomplete MicroPython version data[/yellow]")
        if verbose:
            console.print(f"  Error: {e}")
        console.print()
        return False

    except core.DeviceError as e:
        console.print("[red]✗ Failed to query MicroPython version[/red]")
        if verbose:
            console.print(f"  Error: {e}")
        console.print()
        return False


def check_all_devices(timeout: int, verbose: bool, retry: bool) -> int:
    """
    Check all discovered devices.

    Args:
        timeout: Query timeout in seconds
        verbose: Show detailed error messages
        retry: Retry failed devices

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

        except core.QueryTimeoutError as e:
            failed.append(device.path)
            print_device_info(device)
            console.print("[red]✗ Query timed out[/red]")
            if verbose:
                console.print(f"  Error: {e}")
            console.print()

        except core.ParseError as e:
            failed.append(device.path)
            print_device_info(device)
            console.print("[yellow]⚠ Failed to parse version[/yellow]")
            if verbose:
                console.print(f"  Error: {e}")
            console.print()

        except core.DeviceError as e:
            failed.append(device.path)
            print_device_info(device)
            console.print("[red]✗ Device error[/red]")
            if verbose:
                console.print(f"  Error: {e}")
            console.print()

    # Retry failed devices if requested
    if failed and retry:
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
                console.print("[red]✗ Still failed[/red]")
                if verbose:
                    console.print(f"  Error: {type(e).__name__}: {e}")
                console.print()

        if still_failed > 0:
            console.print(f"[red]{still_failed} device(s) still failed after retry[/red]")
        else:
            console.print("[green]All devices succeeded on retry[/green]")
        console.print()

        return still_failed

    return len(failed)


def list_devices_text(timeout: int, verbose: bool, retry: bool):
    """
    List all devices with full details (queries each device).

    This matches the behavior of the original bash script.
    """
    devices = core.discover_devices()

    if not devices:
        console.print("[yellow]No MicroPython devices found[/yellow]")
        return

    console.print("[blue]Discovering MicroPython devices...[/blue]")
    console.print()
    console.print(f"[blue]Found {len(devices)} device(s)[/blue]")
    console.print()

    # Query all devices
    failed = []
    for device in devices:
        try:
            version = core.query_device(device.path, timeout=timeout)
            print_device_info(device)
            print_version_info(version)

        except core.QueryTimeoutError as e:
            failed.append(device.path)
            print_device_info(device)
            console.print("[red]✗ Query timed out[/red]")
            if verbose:
                console.print(f"  Error: {e}")
            console.print()

        except core.ParseError as e:
            failed.append(device.path)
            print_device_info(device)
            console.print("[yellow]⚠ Failed to parse version[/yellow]")
            if verbose:
                console.print(f"  Error: {e}")
            console.print()

        except core.DeviceError as e:
            failed.append(device.path)
            print_device_info(device)
            console.print("[red]✗ Device error[/red]")
            if verbose:
                console.print(f"  Error: {e}")
            console.print()

    # Retry failed devices if requested
    if failed and retry:
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
                console.print("[red]✗ Still failed[/red]")
                if verbose:
                    console.print(f"  Error: {type(e).__name__}: {e}")
                console.print()

        if still_failed > 0:
            console.print(f"[red]{still_failed} device(s) still failed after retry[/red]")
        else:
            console.print("[green]All devices succeeded on retry[/green]")
        console.print()


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
@click.option("--list", "list_mode", is_flag=True, help="Query and list all devices with full details")
@click.option("--json", "json_mode", is_flag=True, help="Output in JSON format")
@click.option("-v", "--verbose", is_flag=True, help="Show detailed error messages")
@click.option("-t", "--timeout", default=5, help="Query timeout in seconds (default: 5)")
@click.option("--retry", is_flag=True, help="Retry failed devices automatically")
@click.option("--version", "show_version", is_flag=True, help="Show version and exit")
def main(device: Optional[str], list_mode: bool, json_mode: bool,
         verbose: bool, timeout: int, retry: bool, show_version: bool):
    """
    MicroPython device checker and monitor.

    \b
    Usage:
      mpy-devices                 Launch TUI interface
      mpy-devices --list          Query all devices and show full details
      mpy-devices /dev/ttyACM0    Check specific device
      mpy-devices a0              Check device using shortcut
      mpy-devices --json          List devices in JSON format (no query)
      mpy-devices --json a0       Check device and output JSON

    \b
    Shortcuts:
      a0-a9   -> /dev/ttyACM0-9 (Linux), /dev/cu.usbmodem0-9 (macOS)
      u0-u9   -> /dev/ttyUSB0-9 (Linux), /dev/cu.usbserial-0-9 (macOS)
      c0-c99  -> COM0-99 (Windows)
    """
    if show_version:
        console.print(f"mpy-devices {__version__}")
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
        list_devices_text(timeout, verbose, retry)
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
