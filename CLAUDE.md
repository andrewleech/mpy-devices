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
- Future: async device queries, live monitoring

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

### Unit Tests (Future)

```bash
pytest tests/
pytest --cov=mpy_devices
```

Test structure:
- `tests/test_core.py` - Core functionality
- `tests/test_cli.py` - CLI behavior
- `tests/test_tui.py` - TUI components

Mock `serial.tools.list_ports.comports()` and `SerialTransport` for tests.

## Future Enhancements

### Async Device Queries

TUI currently queries devices synchronously, blocking the UI. Future improvement:

```python
async def query_device_async(device_path: str) -> MicroPythonVersion:
    # Use asyncio to query without blocking
    ...

# In TUI
async def query_all_devices(self):
    tasks = [query_device_async(d.path) for d in self.devices]
    results = await asyncio.gather(*tasks, return_exceptions=True)
```

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
- `pyserial` - Device discovery via `list_ports`
- `click` - CLI framework
- `rich` - Pretty console output
- `textual` - TUI framework

**MicroPython:**
- `mpremote` - Optional, for `SerialTransport`
- Fallback: Search for `tools/mpremote` in repo

**Dev:**
- `pytest` - Testing framework
- `black` - Code formatting
- `ruff` - Linting

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
