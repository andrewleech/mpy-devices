# mpy-devices

Query and monitor MicroPython devices - discover connected devices and check firmware versions.

## Features

- **TUI Interface** - Interactive terminal UI for monitoring devices
- **Device Discovery** - Automatic detection of connected MicroPython devices
- **Version Checking** - Query firmware version and device information
- **Multiple Output Formats** - Text, JSON for scripting
- **Stable Device Paths** - Resolves `/dev/serial/by-id/` paths
- **Shortcuts** - Use `a0` instead of `/dev/ttyACM0`

## Installation

### Using uv (Recommended)

```bash
uv tool install mpy-devices
```

### Using pipx

```bash
pipx install mpy-devices
```

### From Source

```bash
git clone https://github.com/andrewleech/mpy-devices
cd mpy-devices
uv pip install -e .
```

## Usage

### TUI Mode (Default)

Launch the interactive terminal UI:

```bash
mpy-devices
```

Features:
- Auto-discover all connected devices
- Live device information
- Keyboard navigation (`↑↓` to navigate, `r` to refresh, `q` to quit)
- Device details panel

### Check Specific Device

```bash
# Check by device path
mpy-devices /dev/ttyACM0

# Check using shortcut
mpy-devices a0

# Check by stable path
mpy-devices /dev/serial/by-id/usb-MicroPython_Board_ABC123-if00
```

Output:
```
Querying: /dev/ttyACM0
  TTY Path:    /dev/ttyACM0
  By-ID Path:  /dev/serial/by-id/usb-Raspberry_Pi_Pico_ABC123-if00
  VID:PID:     2e8a:000c
  Device ID:   ABC123
  Machine:     RPI_PICO with RP2040
  System:      rp2
  Release:     1.22.0
  Version:     v1.22.0 on 2024-01-01
```

### List All Devices

```bash
mpy-devices --list
```

Output:
```
/dev/ttyACM0 ABC123 2e8a:000c Raspberry Pi Pico
/dev/ttyACM1 DEF456 f055:9802 MicroPython pyboard
```

### JSON Output

For scripting and automation:

```bash
# List all devices as JSON
mpy-devices --json

# Check specific device as JSON
mpy-devices --json /dev/ttyACM0
```

Example output:
```json
{
  "device": {
    "path": "/dev/ttyACM0",
    "by_id_path": "/dev/serial/by-id/usb-Raspberry_Pi_Pico_ABC123-if00",
    "serial_number": "ABC123",
    "vid": 11914,
    "pid": 12,
    "vid_pid": "2e8a:000c",
    "manufacturer": "Raspberry Pi",
    "product": "Pico"
  },
  "version": {
    "sysname": "rp2",
    "release": "1.22.0",
    "version": "v1.22.0 on 2024-01-01",
    "machine": "RPI_PICO with RP2040",
    "nodename": "rp2"
  },
  "error": null
}
```

## Device Shortcuts

For convenience, mpy-devices supports mpremote-style shortcuts:

- `a0-a9` → `/dev/ttyACM0-9` (Linux)
- `u0-u9` → `/dev/ttyUSB0-9` (Linux)
- `c0-c99` → `COM0-99` (Windows)

Examples:
```bash
mpy-devices a0       # Same as /dev/ttyACM0
mpy-devices u1       # Same as /dev/ttyUSB1
mpy-devices c3       # Same as COM3
```

## Options

```
-v, --verbose           Show detailed error messages
-t, --timeout SECONDS   Query timeout in seconds (default: 5)
--list                  List all devices (text output)
--json                  Output in JSON format
--version               Show version and exit
--help                  Show help message
```

## Examples

### Check All Connected Devices

```bash
mpy-devices
```

Launches TUI showing all devices with their status.

### Check Device Before Flashing

```bash
mpy-devices /dev/ttyACM0 && flash-firmware.sh /dev/ttyACM0
```

### Monitor Devices in Script

```bash
#!/bin/bash
devices=$(mpy-devices --json | jq -r '.[].path')
for dev in $devices; do
    echo "Found device: $dev"
done
```

### Check Device with Custom Timeout

```bash
mpy-devices --timeout 10 /dev/ttyACM0
```

## Integration with MicroPython Workflow

### Before Running Tests

```bash
# Check device and get stable path
mpy-devices a0

# Use the by-id path in test scripts
cd tests
./run-tests.py -t /dev/serial/by-id/usb-Board-ABC123-if00
```

### In CI/CD

```bash
# Verify device is connected and running MicroPython
if mpy-devices --json /dev/ttyACM0 | jq -e '.version != null'; then
    echo "Device ready"
    run-tests.sh
else
    echo "Device not ready"
    exit 1
fi
```

## Troubleshooting

### No Devices Found

- Check USB cable connection
- Verify device is powered on
- Check permissions (see below)

### Permission Denied

On Linux, add your user to the `dialout` group:

```bash
sudo usermod -a -G dialout $USER
```

Then logout and login again.

### Device Not Responding

- Try with longer timeout: `mpy-devices --timeout 10 /dev/ttyACM0`
- Check if another program is using the device
- Try soft reset: `mpremote connect /dev/ttyACM0 soft-reset`

### mpremote Not Found

Install mpremote:

```bash
pip install mpremote
```

Or if running from MicroPython repository:

```bash
cd micropython/tools/mpremote
pip install -e .
```

## Requirements

- Python 3.8+
- pyserial
- mpremote (for device querying)
- click, rich, textual (for UI)

## Development

See [CLAUDE.md](CLAUDE.md) for development documentation.

```bash
# Clone repository
git clone https://github.com/andrewleech/mpy-devices
cd mpy-devices

# Install in development mode
uv venv
source .venv/bin/activate
uv pip install -e ".[dev]"

# Run tests
pytest

# Format code
black src/
ruff check src/
```

## License

MIT License - See LICENSE file for details.

## Related Projects

- [mpremote](https://docs.micropython.org/en/latest/reference/mpremote.html) - MicroPython remote control and filesystem access
- [MicroPython](https://micropython.org/) - Python for microcontrollers

## Contributing

Contributions welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## Author

Andrew Leech

## Changelog

### 0.1.0 (2024-10-22)

- Initial release
- TUI interface with live device list
- Text and JSON output modes
- Device discovery and version checking
- Shortcut support (a0, u0, c0, etc.)
- Stable /dev/serial/by-id/ path resolution
