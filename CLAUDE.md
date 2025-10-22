# mpy-devices CLAUDE.md

This file provides context for AI coding agents working on the mpy-devices package.

## Project Overview

**mpy-devices** is a tool for discovering and querying MicroPython devices connected to your system. It provides both a text-based CLI and an interactive TUI for monitoring devices.

### Goals

1. **Robust device discovery** - Use pyserial's `list_ports` API (no text parsing)
2. **Reliable querying** - Use mpremote's `SerialTransport` directly
3. **User-friendly** - TUI as default, text output for scripting
4. **Maintainable** - Type hints, clear separation of concerns
5. **Extensible** - Easy to add features like monitoring, automation
6. **Cross-platform** - Full support for Linux, macOS, and Windows

### Why Python over Bash?

The original bash script parsed `mpremote connect list` text output, which is fragile. This Python implementation:
- Uses `serial.tools.list_ports` API directly (stable, structured data)
- Imports mpremote's `SerialTransport` class (no subprocess parsing)
- Eliminates parsing fragility from mpremote output format changes
- Easier to extend with TUI, JSON output, async queries, etc.

## Architecture

### Module Structure

```
src/mpy_devices/
├── __init__.py          # Package exports
├── __main__.py          # Entry point for python -m mpy_devices
├── core.py              # Device discovery and querying logic
├── cli.py               # Command-line interface (Click + Rich)
└── tui.py               # Terminal UI (Textual)
```

### Separation of Concerns

**core.py** - Pure business logic
- Data classes: `DeviceInfo`, `MicroPythonVersion`
- Functions: `discover_devices()`, `query_device()`, `find_device()`
- No CLI dependencies, can be imported as library
- All functions have type hints and docstrings

**cli.py** - Command-line interface
- Uses Click for argument parsing
- Uses Rich for pretty console output
- Handles CLI logic (--list, --json, device arg)
- Delegates to TUI when no args provided

**tui.py** - Textual TUI application
- Interactive device list with live refresh
- Device detail panel
- Keyboard navigation (r=refresh, q=quit)
- Async device queries using Textual's worker threads
- Shows UI immediately, devices update as queries complete
- Parallel device queries for improved performance

## Development Setup

### Using uv (Recommended)

```bash
# Clone/navigate to project
cd ~/mpy-devices

# Create virtual environment and install dependencies
uv venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows
uv pip install -e ".[dev]"

# Run the tool
mpy-devices
# or
python -m mpy_devices
```

### Using pip/pipx

```bash
# Install from local directory
pip install -e ~/mpy-devices

# Or for user installation
pipx install ~/mpy-devices

# Run
mpy-devices
```

## Code Patterns

### Data Classes

Use `@dataclass` for structured data:

```python
@dataclass
class DeviceInfo:
    path: str
    serial_number: Optional[str] = None
    vid: Optional[int] = None
    # ...
```

### Error Handling

Custom exception hierarchy:

```python
class DeviceError(Exception): pass
class DeviceNotFoundError(DeviceError): pass
class QueryTimeoutError(DeviceError): pass
class ParseError(DeviceError): pass
```

All functions that can fail raise specific exceptions, not generic ones.

### Type Hints

All functions have complete type hints:

```python
def discover_devices(include_ttyS: bool = False) -> List[DeviceInfo]:
    """..."""
```

This enables IDE autocomplete and type checking with mypy.

### Device Discovery

Uses pyserial's stable API:

```python
import serial.tools.list_ports

for port in serial.tools.list_ports.comports():
    device = DeviceInfo(
        path=port.device,
        serial_number=port.serial_number,
        vid=port.vid,
        # ... all fields from ListPortInfo
    )
```

**No text parsing!** All data comes from structured port objects.

### Device Querying

Uses mpremote's `SerialTransport` directly:

```python
from mpremote.transport_serial import SerialTransport

transport = SerialTransport(device_path, baudrate=115200)
transport.enter_raw_repl(soft_reset=False)
output, _ = transport.exec_raw("import os; print(os.uname())")
transport.exit_raw_repl()
transport.close()
```

This is what mpremote itself uses internally - we just import it directly.

### Platform Support

The tool supports Linux, macOS, and Windows with platform-specific handling:

**Linux:**
- Device paths: `/dev/ttyACM*`, `/dev/ttyUSB*`
- Shortcuts: `a0` → `/dev/ttyACM0`, `u0` → `/dev/ttyUSB0`
- By-ID paths: `/dev/serial/by-id/*` (stable device references)
- Filters built-in serial ports (`/dev/ttyS*`) by default

**macOS:**
- Device paths: `/dev/cu.usbmodem*`, `/dev/cu.usbserial*`
- Shortcuts: `a0` → `/dev/cu.usbmodem0`, `u0` → `/dev/cu.usbserial-0`
- Filters `/dev/tty.*` devices (keeps only `/dev/cu.*`)

**Windows:**
- Device paths: `COM1`, `COM2`, etc.
- Shortcuts: `c1` → `COM1`, `c10` → `COM10`

Platform detection uses `sys.platform` to apply appropriate filtering and path resolution.

### Parsing os.uname()

Robust regex parsing with fallbacks:

```python
def extract_field(text: str, field: str) -> Optional[str]:
    patterns = [
        rf"{field}='([^']*)'",  # Single quotes
        rf'{field}="([^"]*)"',  # Double quotes
    ]
    for pattern in patterns:
        if match := re.search(pattern, text):
            return match.group(1)
    return None
```

Handles both quote styles and missing fields gracefully.

## CLI Behavior

### Default: TUI

```bash
$ mpy-devices
# Launches interactive TUI
```

### Device Check

```bash
$ mpy-devices /dev/ttyACM0
Querying: /dev/ttyACM0
  TTY Path:    /dev/ttyACM0
  By-ID Path:  /dev/serial/by-id/usb-...
  VID:PID:     2e8a:000c
  Device ID:   ABC123
  Machine:     RPI_PICO with RP2040
  System:      rp2
  Release:     1.22.0
  Version:     v1.22.0 on 2024-01-01
```

### List Mode

```bash
$ mpy-devices --list
/dev/ttyACM0 ABC123 2e8a:000c Raspberry Pi Pico
/dev/ttyACM1 DEF456 f055:9802 pyboard
```

### JSON Mode

```bash
$ mpy-devices --json
[
  {
    "path": "/dev/ttyACM0",
    "serial_number": "ABC123",
    "vid_pid": "2e8a:000c",
    "manufacturer": "Raspberry Pi",
    ...
  }
]

$ mpy-devices --json /dev/ttyACM0
{
  "device": { "path": "/dev/ttyACM0", ... },
  "version": { "machine": "RPI_PICO with RP2040", ... },
  "error": null
}
```

### Retry Flag

The `--retry` flag enables automatic retry of failed device queries:

```bash
$ mpy-devices --list --retry
# Failed devices will be retried automatically
```

By default, failed devices are not retried. Use this flag when working with flaky connections or during initial device enumeration.

## Testing

### Manual Testing

```bash
# Test device discovery
python -c "from mpy_devices import discover_devices; print(discover_devices())"

# Test device query
python -c "from mpy_devices import query_device; print(query_device('/dev/ttyACM0'))"

# Test CLI
mpy-devices --list
mpy-devices --json
mpy-devices /dev/ttyACM0
```

### Unit Tests

```bash
pytest tests/
pytest --cov=mpy_devices
```

Test structure:
- `tests/test_core.py` - Core functionality (shortcut resolution, parsing, data classes)
- `tests/test_cli.py` - CLI behavior (flags, arguments, output formats)
- `tests/test_platform.py` - Platform-specific behavior (shortcuts, filtering)

Tests use mocking for `serial.tools.list_ports.comports()` and `SerialTransport` to avoid requiring real hardware.

## TUI Implementation

### Async Device Queries

The TUI uses Textual's `@work` decorator for non-blocking device queries:

```python
@work(thread=True, exclusive=False)
def query_device_worker(self, device: core.DeviceInfo) -> None:
    """Query a single device in a background thread."""
    try:
        version = core.query_device(device.path, timeout=self.timeout)
        self.call_from_thread(self.update_device_success, device, version)
    except Exception as e:
        self.call_from_thread(self.update_device_failure, device, str(e))
```

**Key features:**
- UI shows immediately after device discovery
- Devices queried sequentially in background thread (avoids conflicts)
- Table updates as each query completes
- Status bar shows real-time progress (e.g., "Querying... 3/5 (2 OK, 1 failed)")
- User can interact with UI while queries run
- Arrow keys update details panel without re-querying
- Enter key re-queries the selected device
- Worker cancellation on refresh

**Why sequential queries?**
Some devices are accessible via multiple TTY paths (e.g., `/dev/ttyACM0` and `/dev/ttyACM1` for the same physical device). Querying them simultaneously causes conflicts. Sequential querying ensures only one device is accessed at a time.

## Future Enhancements

### Live Monitoring

Add auto-refresh and change detection:

```python
class MPyDevicesApp(App):
    def on_mount(self):
        self.set_interval(5.0, self.action_refresh)
```

### Device Actions

Add commands in TUI:
- `f` - Flash firmware
- `t` - Run tests
- `r` - Soft reset
- `b` - Enter bootloader

### Filtering

```bash
mpy-devices --filter "rp2"  # Show only RP2040 devices
mpy-devices --filter "2e8a:000c"  # Show specific VID:PID
```

### Configuration File

Support `~/.config/mpy-devices/config.toml`:

```toml
[defaults]
timeout = 10
auto_refresh = true

[filters]
exclude_ttyS = true
only_micropython = true
```

## Common Development Tasks

### Adding a New Field to DeviceInfo

1. Add field to dataclass in `core.py`
2. Extract field in `discover_devices()`
3. Display field in `cli.py` (text output)
4. Add column to TUI table in `tui.py`
5. Add to JSON output in `cli.py`

### Adding a New CLI Flag

1. Add option to `@click.command()` in `cli.py`
2. Handle option in `main()` function
3. Update help text and docstring
4. Update README.md usage section

### Adding a New TUI Feature

1. Add widget/component in `tui.py`
2. Add to `compose()` method
3. Add event handler (`on_*` method)
4. Add key binding in `BINDINGS`
5. Update CSS if needed

## Dependencies

**Core:**
- `pyserial>=3.5` - Device discovery via `list_ports`
- `click>=8.0` - CLI framework
- `rich>=13.0` - Pretty console output
- `textual>=0.50` - TUI framework
- `mpremote>=1.20` - MicroPython device communication via `SerialTransport`

**Dev:**
- `pytest>=7.0` - Testing framework
- `pytest-cov>=4.0` - Test coverage
- `black>=23.0` - Code formatting
- `ruff>=0.1.0` - Linting

**Version Management:**
- Version is dynamically sourced from `src/mpy_devices/__init__.py`
- Configured in `pyproject.toml` with `dynamic = ["version"]`
- Single source of truth prevents version drift

## Code Style

- Line length: 99 characters
- Type hints on all functions
- Docstrings in Google style
- Format with `black`
- Lint with `ruff`

```bash
black src/
ruff check src/
```

## Publishing

### To PyPI

```bash
# Build
python -m build

# Upload
twine upload dist/*
```

### To GitHub

```bash
git tag v0.1.0
git push origin v0.1.0
```

Then users can install with:

```bash
uv tool install mpy-devices
# or
pipx install mpy-devices
```

## Troubleshooting

### ImportError: mpremote not found

```bash
# Install mpremote
pip install mpremote

# Or run from MicroPython repo
cd ~/micropython/tools/mpremote
pip install -e .
```

### Permission denied on /dev/ttyACM0

```bash
# Linux: Add user to dialout group
sudo usermod -a -G dialout $USER
# Then logout/login
```

### TUI not working

```bash
# Check terminal supports 256 colors
echo $TERM  # Should be xterm-256color or similar

# Try without TUI
mpy-devices --list
```

## License

MIT License - See LICENSE file for details.
