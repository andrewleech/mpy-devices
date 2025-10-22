"""Tests for core functionality."""

import pytest

from mpy_devices import core


class TestShortcutResolution:
    """Test device shortcut resolution."""

    def test_resolve_linux_acm(self):
        """Test Linux ACM shortcut resolution."""
        # Would need platform mocking
        pass

    def test_resolve_linux_usb(self):
        """Test Linux USB shortcut resolution."""
        pass

    def test_resolve_windows_com(self):
        """Test Windows COM port shortcut resolution."""
        result = core.resolve_shortcut("c5")
        assert result == "COM5"

    def test_resolve_no_shortcut(self):
        """Test non-shortcut path passes through."""
        path = "/dev/ttyACM0"
        assert core.resolve_shortcut(path) == path


class TestUnameParser:
    """Test os.uname() output parsing."""

    def test_parse_valid_single_quotes(self):
        """Test parsing with single-quoted fields."""
        output = "(sysname='rp2', nodename='rp2', release='1.22.0', version='v1.22.0 on 2024-01-01', machine='RPI_PICO with RP2040')"
        result = core.parse_uname_output(output)

        assert result.sysname == "rp2"
        assert result.release == "1.22.0"
        assert result.version == "v1.22.0 on 2024-01-01"
        assert result.machine == "RPI_PICO with RP2040"
        assert result.nodename == "rp2"

    def test_parse_valid_double_quotes(self):
        """Test parsing with double-quoted fields."""
        output = '(sysname="rp2", release="1.22.0", version="v1.22.0", machine="RPI_PICO")'
        result = core.parse_uname_output(output)

        assert result.sysname == "rp2"
        assert result.release == "1.22.0"

    def test_parse_incomplete_raises_error(self):
        """Test that incomplete data raises ParseError."""
        output = "(sysname='rp2')"

        with pytest.raises(core.ParseError):
            core.parse_uname_output(output)

    def test_parse_missing_field_uses_unknown(self):
        """Test that missing optional fields are handled."""
        # Valid output without nodename
        output = "(sysname='rp2', release='1.22.0', version='v1.22.0', machine='RPI_PICO')"
        result = core.parse_uname_output(output)

        assert result.nodename is None
        assert result.is_complete()


class TestDeviceInfo:
    """Test DeviceInfo dataclass."""

    def test_vid_pid_str_format(self):
        """Test VID:PID string formatting."""
        device = core.DeviceInfo(
            path="/dev/ttyACM0",
            vid=0x2e8a,
            pid=0x000c
        )
        assert device.vid_pid_str == "2e8a:000c"

    def test_vid_pid_str_none(self):
        """Test VID:PID string when values are None."""
        device = core.DeviceInfo(path="/dev/ttyACM0")
        assert device.vid_pid_str is None


class TestPlatformSupport:
    """Test platform-specific behavior."""

    def test_by_id_path_non_linux(self):
        """Test that by-id paths return None on non-Linux."""
        # Would need platform mocking
        pass

    def test_device_filtering_linux(self):
        """Test Linux device filtering."""
        # Would need mocking of serial.tools.list_ports
        pass


# Placeholder for integration tests
class TestDeviceQuery:
    """Test device querying functionality."""

    def test_query_device_timeout(self):
        """Test query timeout handling."""
        # Would need device mocking or real hardware
        pass

    def test_query_device_parse_error(self):
        """Test handling of parse errors."""
        pass
