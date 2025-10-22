"""Textual TUI interface for mpy-devices."""

from datetime import datetime
from typing import Dict, List, Optional

from textual import work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Vertical
from textual.widgets import DataTable, Footer, Header, Static
from textual.worker import Worker, WorkerState

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
        """Display error information with all available device details."""
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

        lines.append("")
        lines.append(f"[red]Error:[/red] {error}")
        self.update("\n".join(lines))

    def show_querying(self, device: core.DeviceInfo):
        """Show that device is being queried with all available device details."""
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
        layout: vertical;
    }

    Header {
        dock: top;
    }

    #device-list {
        height: 60%;
        border: solid $accent;
    }

    #details-panel {
        height: 40%;
        border: solid $accent;
        padding: 1;
    }

    #status-bar {
        dock: bottom;
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
        Binding("r", "refresh", "Refresh All"),
        Binding("enter", "select_cursor", "Refresh Device"),
        Binding("q", "quit", "Quit"),
        Binding("?", "help", "Help"),
    ]

    TITLE = "MicroPython Devices"

    def __init__(self, timeout: int = 5):
        super().__init__()
        self.timeout = timeout
        self.devices: List[core.DeviceInfo] = []
        self.versions: dict = {}  # device.path -> MicroPythonVersion or error
        self.active_workers: List[Worker] = []  # Track workers for cancellation
        self.query_stats: Dict[str, int] = {
            "total": 0,
            "completed": 0,
            "success": 0,
            "failed": 0,
        }

    def compose(self) -> ComposeResult:
        """Create child widgets."""
        yield Header()

        with Container(id="device-list"):
            yield DeviceList()

        with Vertical(id="details-panel"):
            yield DeviceDetails()

        with Container(id="status-bar"):
            yield Static("", classes="status-text")

        yield Footer()

    def on_mount(self) -> None:
        """Set up the application on mount."""
        table = self.query_one(DeviceList)

        # Set up table columns
        table.add_column("Device", key="device", width=20)
        table.add_column("Serial", key="serial", width=15)
        table.add_column("VID:PID", key="vid_pid", width=10)
        table.add_column("Board", key="board")  # Auto-scale to fit screen
        table.add_column("Status", key="status", width=10)

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
            # Don't add a selectable row for empty state
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

        # Select first device to show details immediately
        if self.devices:
            table.move_cursor(row=0)

        # Start querying devices in parallel (non-blocking)
        self.start_device_queries()

    def start_device_queries(self) -> None:
        """
        Start querying all devices sequentially in a background thread.

        Devices are queried one at a time to avoid conflicts when the same
        physical device is accessible via multiple TTY paths.
        """
        # Cancel any existing workers from previous refresh
        self.cancel_workers()

        # Reset statistics
        self.query_stats = {
            "total": len(self.devices),
            "completed": 0,
            "success": 0,
            "failed": 0,
        }

        # Spawn a single worker that queries all devices sequentially
        worker = self.query_all_devices_worker()
        self.active_workers.append(worker)

        self.update_status(f"Querying {len(self.devices)} device(s)...")

    @work(thread=True, exclusive=False)
    def query_all_devices_worker(self) -> None:
        """
        Query all devices sequentially in a background thread.

        Queries one device at a time to avoid conflicts when the same
        physical device is accessible via multiple TTY paths.
        """
        for device in self.devices:
            try:
                version = core.query_device(device.path, timeout=self.timeout)
                # Update UI from thread
                self.call_from_thread(self.update_device_success, device, version)

            except Exception as e:
                # Update UI from thread
                self.call_from_thread(self.update_device_failure, device, str(e))

    @work(thread=True, exclusive=False)
    def refresh_single_device_worker(self, device: core.DeviceInfo) -> None:
        """
        Re-query a single device in a background thread.

        Used when user presses Enter to refresh a specific device.
        """
        # Mark device as querying
        self.call_from_thread(self.mark_device_querying, device)

        try:
            version = core.query_device(device.path, timeout=self.timeout)
            # Update UI from thread
            self.call_from_thread(self.update_device_success, device, version)

        except Exception as e:
            # Update UI from thread
            self.call_from_thread(self.update_device_failure, device, str(e))

    def mark_device_querying(self, device: core.DeviceInfo) -> None:
        """Mark a device as being queried (called from main thread)."""
        table = self.query_one(DeviceList)

        # Clear version from cache
        if device.path in self.versions:
            del self.versions[device.path]

        # Update table row to show querying status
        table.update_cell(device.path, "board", "")
        table.update_cell(device.path, "status", "[yellow]⟳ querying...[/yellow]")

        # Update details if this device is currently selected
        if table.cursor_row is not None:
            row_key = table.get_row_at(table.cursor_row)[0]
            if hasattr(row_key, 'value') and row_key.value == device.path:
                details = self.query_one(DeviceDetails)
                details.show_querying(device)

    def update_device_success(self, device: core.DeviceInfo, version: core.MicroPythonVersion) -> None:
        """Update UI when device query succeeds (called from main thread)."""
        table = self.query_one(DeviceList)

        # Store version
        self.versions[device.path] = version

        # Extract board name (first part of machine)
        board = version.machine.split()[0] if version.machine else "Unknown"

        # Update table row
        table.update_cell(device.path, "board", board)
        table.update_cell(device.path, "status", "[green]✓[/green]")

        # Update statistics
        self.query_stats["completed"] += 1
        self.query_stats["success"] += 1
        self.update_query_status()

        # Update details if this device is currently selected
        if table.cursor_row is not None:
            row_key = table.get_row_at(table.cursor_row)[0]
            if hasattr(row_key, 'value') and row_key.value == device.path:
                details = self.query_one(DeviceDetails)
                details.show_device(device, version)

    def update_device_failure(self, device: core.DeviceInfo, error: str) -> None:
        """Update UI when device query fails (called from main thread)."""
        table = self.query_one(DeviceList)

        # Store error
        self.versions[device.path] = error

        # Update table row
        table.update_cell(device.path, "status", "[red]✗[/red]")

        # Update statistics
        self.query_stats["completed"] += 1
        self.query_stats["failed"] += 1
        self.update_query_status()

        # Update details if this device is currently selected
        if table.cursor_row is not None:
            row_key = table.get_row_at(table.cursor_row)[0]
            if hasattr(row_key, 'value') and row_key.value == device.path:
                details = self.query_one(DeviceDetails)
                details.show_error(device, error)

    def update_query_status(self) -> None:
        """Update status bar with current query progress."""
        stats = self.query_stats
        total = stats["total"]
        completed = stats["completed"]
        success = stats["success"]
        failed = stats["failed"]

        if completed < total:
            # Still querying
            self.update_status(
                f"Querying... {completed}/{total} "
                f"([green]{success} OK[/green], [red]{failed} failed[/red])"
            )
        else:
            # All queries complete
            status_parts = []
            if success > 0:
                status_parts.append(f"[green]{success} OK[/green]")
            if failed > 0:
                status_parts.append(f"[red]{failed} failed[/red]")

            self.update_status(
                f"{' | '.join(status_parts)} - {datetime.now().strftime('%H:%M:%S')}"
            )

    def cancel_workers(self) -> None:
        """Cancel all active worker threads."""
        for worker in self.active_workers:
            if worker.state not in (WorkerState.SUCCESS, WorkerState.ERROR, WorkerState.CANCELLED):
                worker.cancel()
        self.active_workers.clear()

    def on_data_table_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
        """Handle device cursor movement (arrow keys)."""
        self._show_device_details(event.row_key)

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """Handle device selection (Enter key) - re-query the device."""
        # Get device path from row key
        if not event.row_key or not hasattr(event.row_key, 'value'):
            return

        device_path = event.row_key.value

        # Find device
        device = None
        for d in self.devices:
            if d.path == device_path:
                device = d
                break

        if not device:
            return

        # Refresh this device
        self.refresh_single_device_worker(device)

    def _show_device_details(self, row_key) -> None:
        """Show device details for the given row key."""
        details = self.query_one(DeviceDetails)

        # Get device (safely handle empty/invalid selection)
        if not row_key or not hasattr(row_key, 'value'):
            return

        device_path = row_key.value

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
            # Query complete with success
            details.show_device(device, version_or_error)
        elif isinstance(version_or_error, str):
            # Query complete with error
            details.show_error(device, version_or_error)
        else:
            # Query still in progress
            details.show_querying(device)

    def action_help(self) -> None:
        """Show help message."""
        self.update_status(
            "Keys: [b]r[/b]=refresh all [b]Enter[/b]=refresh device [b]↑↓[/b]=navigate [b]q[/b]=quit"
        )

    def update_status(self, message: str) -> None:
        """Update status bar message."""
        status = self.query_one("#status-bar Static")
        status.update(message)


def run_tui(timeout: int = 5):
    """Run the TUI application."""
    app = MPyDevicesApp(timeout=timeout)
    app.run()
