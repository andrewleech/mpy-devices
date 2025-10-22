"""Tests for platform-specific behavior."""

import sys

from mpy_devices import core


class TestShortcutPlatforms:
    """Test shortcut resolution across platforms."""

    def test_current_platform_shortcuts(self):
        """Test shortcuts work on current platform."""
        # Test Windows COM ports always work
        assert core.resolve_shortcut("c10") == "COM10"

        # Platform-specific shortcuts
        if sys.platform == "linux":
            assert core.resolve_shortcut("a0") == "/dev/ttyACM0"
            assert core.resolve_shortcut("u0") == "/dev/ttyUSB0"
        elif sys.platform == "darwin":
            assert "/dev/cu." in core.resolve_shortcut("a0")
            assert "/dev/cu." in core.resolve_shortcut("u0")


class TestByIdPaths:
    """Test by-id path resolution."""

    def test_by_id_returns_none_on_non_linux(self):
        """Test by-id paths return None on non-Linux platforms."""
        if sys.platform != "linux":
            result = core.resolve_by_id_path("/dev/ttyACM0")
            assert result is None

    def test_by_id_linux_nonexistent_dir(self):
        """Test by-id with non-existent directory."""
        if sys.platform == "linux":
            # With non-existent device, should return None
            result = core.resolve_by_id_path("/dev/ttyACM999")
            # Either None or a valid path, shouldn't crash
            assert result is None or result.startswith("/dev/serial/by-id/")


class TestDeviceFiltering:
    """Test platform-specific device filtering."""

    def test_discover_devices_no_crash(self):
        """Test that device discovery doesn't crash on any platform."""
        devices = core.discover_devices()
        # Should return a list (possibly empty) without crashing
        assert isinstance(devices, list)

    def test_discover_devices_include_builtin(self):
        """Test include_ttyS parameter."""
        devices_without = core.discover_devices(include_ttyS=False)
        devices_with = core.discover_devices(include_ttyS=True)

        # Both should be lists
        assert isinstance(devices_without, list)
        assert isinstance(devices_with, list)

        # With should have >= without (or equal if no built-in ports)
        assert len(devices_with) >= len(devices_without)
