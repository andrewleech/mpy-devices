"""Textual TUI interface for mpy-devices."""

from datetime import datetime
from typing import List, Optional

from textual.app import App, ComposeResult
from textual.containers import Container, Vertical, Horizontal
from textual.widgets import Header, Footer, DataTable, Static, Button
from textual.binding import Binding

from . import core


class DeviceList(DataTable):
    """Table widget for displaying devices."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.cursor_type = "row"


class DeviceDetails(Static):
    """Widget for showing detailed device information."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.border_title = "Device Details"

    def show_device(self, device: core.DeviceInfo, version: Optional[core.MicroPythonVersion] = None):
        """Display device information."""
        lines = []

        lines.append(f"[b]TTY Path:[/b] {device.path}")

        if device.by_id_path:
            lines.append(f"[b]By-ID Path:[/b] {device.by_id_path}")

        if device.vid_pid_str:
            lines.append(f"[b]VID:PID:[/b] {device.vid_pid_str}")

        if device.serial_number:
            lines.append(f"[b]Serial Number:[/b] {device.serial_number}")

        if device.manufacturer:
            lines.append(f"[b]Manufacturer:[/b] {device.manufacturer}")

        if device.product:
            lines.append(f"[b]Product:[/b] {device.product}")

        if version:
            lines.append("")
            lines.append("[b cyan]MicroPython Version:[/b cyan]")
            lines.append(f"  [b]Machine:[/b] {version.machine}")
            lines.append(f"  [b]System:[/b] {version.sysname}")
            lines.append(f"  [b]Release:[/b] {version.release}")
            lines.append(f"  [b]Version:[/b] {version.version}")

        self.update("\n".join(lines))

    def show_error(self, device: core.DeviceInfo, error: str):
        """Display error information."""
        lines = []
        lines.append(f"[b]TTY Path:[/b] {device.path}")
        lines.append("")
        lines.append(f"[red]Error:[/red] {error}")
        self.update("\n".join(lines))

    def show_querying(self, device: core.DeviceInfo):
        """Show that device is being queried."""
        lines = []
        lines.append(f"[b]TTY Path:[/b] {device.path}")
        lines.append("")
        lines.append("[yellow]Querying device...[/yellow]")
        self.update("\n".join(lines))

    def clear_details(self):
        """Clear the details panel."""
        self.update("Select a device to view details")


class MPyDevicesApp(App):
    """Main TUI application."""

    CSS = """
    Screen {
        layout: grid;
        grid-size: 2 2;
        grid-rows: 1fr 3fr;
    }

    #header-container {
        column-span: 2;
        height: 3;
    }

    #device-list {
        row-span: 2;
    }

    #details-panel {
        border: solid $accent;
        padding: 1;
    }

    #status-bar {
        background: $surface;
        color: $text;
        padding: 0 1;
        height: 3;
    }

    DataTable {
        height: 100%;
    }

    .status-text {
        padding: 1 0;
    }
    """

    BINDINGS = [
        Binding("r", "refresh", "Refresh"),
        Binding("q", "quit", "Quit"),
        Binding("?", "help", "Help"),
    ]

    TITLE = "MicroPython Devices"

    def __init__(self, timeout: int = 5):
        super().__init__()
        self.timeout = timeout
        self.devices: List[core.DeviceInfo] = []
        self.versions: dict = {}  # device.path -> MicroPythonVersion or error

    def compose(self) -> ComposeResult:
        """Create child widgets."""
        yield Header()

        with Container(id="device-list"):
            yield DeviceList()

        with Vertical(id="details-panel"):
            yield DeviceDetails()

        with Container(id="status-bar"):
            yield Static("Press [b]r[/b] to refresh, [b]q[/b] to quit", classes="status-text")

        yield Footer()

    def on_mount(self) -> None:
        """Set up the application on mount."""
        table = self.query_one(DeviceList)

        # Set up table columns
        table.add_column("Device", key="device")
        table.add_column("Serial", key="serial")
        table.add_column("VID:PID", key="vid_pid")
        table.add_column("Board", key="board")
        table.add_column("Status", key="status")

        # Load devices
        self.action_refresh()

    def action_refresh(self) -> None:
        """Refresh the device list."""
        table = self.query_one(DeviceList)
        details = self.query_one(DeviceDetails)

        # Clear existing data
        table.clear()
        self.devices = []
        self.versions = {}
        details.clear_details()

        # Discover devices
        self.devices = core.discover_devices()

        if not self.devices:
            table.add_row("No devices found", "", "", "", "")
            self.update_status(f"No devices found - {datetime.now().strftime('%H:%M:%S')}")
            return

        # Add devices to table
        for device in self.devices:
            table.add_row(
                device.path,
                device.serial_number or "",
                device.vid_pid_str or "",
                "",  # Board - will be filled after query
                "[yellow]⟳ querying...[/yellow]",
                key=device.path,
            )

        self.update_status(f"Found {len(self.devices)} device(s) - Querying...")

        # Query devices in background
        self.query_all_devices()

    def query_all_devices(self) -> None:
        """Query all devices for version information."""
        # Note: This is a simplified synchronous version
        # In a full implementation, you'd want to use asyncio workers
        # to query devices in parallel without blocking the UI

        table = self.query_one(DeviceList)

        success_count = 0
        failed_count = 0

        for device in self.devices:
            try:
                version = core.query_device(device.path, timeout=self.timeout)
                self.versions[device.path] = version

                # Extract board name (first part of machine)
                board = version.machine.split()[0] if version.machine else "Unknown"

                # Update table row
                table.update_cell(device.path, "board", board)
                table.update_cell(device.path, "status", "[green]✓[/green]")

                success_count += 1

            except Exception as e:
                self.versions[device.path] = str(e)

                table.update_cell(device.path, "status", "[red]✗[/red]")

                failed_count += 1

        # Update status
        status_parts = []
        if success_count > 0:
            status_parts.append(f"[green]{success_count} OK[/green]")
        if failed_count > 0:
            status_parts.append(f"[red]{failed_count} failed[/red]")

        self.update_status(
            f"{' | '.join(status_parts)} - {datetime.now().strftime('%H:%M:%S')}"
        )

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """Handle device selection."""
        details = self.query_one(DeviceDetails)

        # Get selected device
        device_path = event.row_key.value

        # Find device
        device = None
        for d in self.devices:
            if d.path == device_path:
                device = d
                break

        if not device:
            return

        # Show device details
        version_or_error = self.versions.get(device_path)

        if isinstance(version_or_error, core.MicroPythonVersion):
            details.show_device(device, version_or_error)
        elif isinstance(version_or_error, str):
            details.show_error(device, version_or_error)
        else:
            details.show_device(device, None)

    def action_help(self) -> None:
        """Show help message."""
        self.update_status(
            "Keys: [b]r[/b]=refresh [b]q[/b]=quit [b]↑↓[/b]=navigate [b]Enter[/b]=details"
        )

    def update_status(self, message: str) -> None:
        """Update status bar message."""
        status = self.query_one("#status-bar Static")
        status.update(message)


def run_tui(timeout: int = 5):
    """Run the TUI application."""
    app = MPyDevicesApp(timeout=timeout)
    app.run()
