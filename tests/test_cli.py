"""Tests for CLI functionality."""

from click.testing import CliRunner

from mpy_devices.cli import main


class TestCLIBasics:
    """Test basic CLI functionality."""

    def test_version_flag(self):
        """Test --version flag."""
        runner = CliRunner()
        result = runner.invoke(main, ["--version"])

        assert result.exit_code == 0
        assert "mpy-devices" in result.output

    def test_help_flag(self):
        """Test --help flag."""
        runner = CliRunner()
        result = runner.invoke(main, ["--help"])

        assert result.exit_code == 0
        assert "MicroPython device checker" in result.output
        assert "--list" in result.output
        assert "--retry" in result.output


class TestListMode:
    """Test device listing."""

    def test_list_mode(self):
        """Test --list flag."""
        # Would need device mocking
        runner = CliRunner()
        result = runner.invoke(main, ["--list"])

        # Should not crash at least
        assert result.exit_code == 0

    def test_json_mode(self):
        """Test --json flag."""
        runner = CliRunner()
        result = runner.invoke(main, ["--json"])

        assert result.exit_code == 0


class TestRetryFlag:
    """Test retry functionality."""

    def test_retry_flag_accepted(self):
        """Test that --retry flag is accepted."""
        runner = CliRunner()
        # This will fail without devices, but should accept the flag
        result = runner.invoke(main, ["--list", "--retry"])

        # Flag should be recognized (no "no such option" error)
        assert "no such option" not in result.output.lower()
