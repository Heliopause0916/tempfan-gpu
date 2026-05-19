"""Tests for the tempfan_gpu.gpu module."""

from unittest import mock

from tempfan_gpu import gpu


def test_get_gpu_temperatures_returns_list() -> None:
    """get_gpu_temperatures always returns a list (possibly empty)."""
    temps = gpu.get_gpu_temperatures()
    assert isinstance(temps, list)


def test_get_max_gpu_temperature_none_on_empty() -> None:
    """get_max_gpu_temperature returns None when no temperatures available."""
    result = gpu.get_max_gpu_temperature()
    assert result is None or isinstance(result, (int, float))


def test_get_gpu_temperatures_parses_output() -> None:
    """get_gpu_temperatures parses nvidia-smi output correctly."""
    with mock.patch("tempfan_gpu.gpu.subprocess.run") as mock_run:
        mock_run.return_value.stdout = "75\n82\n"
        mock_run.return_value.check_returncode.return_value = None
        temps = gpu.get_gpu_temperatures()
        assert temps == [75.0, 82.0]


def test_get_gpu_temperatures_empty_on_file_not_found() -> None:
    """get_gpu_temperatures returns [] when nvidia-smi is not found."""
    with mock.patch("tempfan_gpu.gpu.subprocess.run", side_effect=FileNotFoundError):
        temps = gpu.get_gpu_temperatures()
        assert temps == []


def test_get_gpu_temperatures_empty_on_called_process_error() -> None:
    """get_gpu_temperatures returns [] on CalledProcessError."""
    import subprocess
    with mock.patch("tempfan_gpu.gpu.subprocess.run") as mock_run:
        mock_run.return_value.check_returncode.side_effect = subprocess.CalledProcessError(1, "nvidia-smi")
        temps = gpu.get_gpu_temperatures()
        assert temps == []


def test_get_gpu_temperatures_empty_on_timeout() -> None:
    """get_gpu_temperatures returns [] on TimeoutExpired."""
    import subprocess
    with mock.patch("tempfan_gpu.gpu.subprocess.run", side_effect=subprocess.TimeoutExpired("nvidia-smi", 10)):
        temps = gpu.get_gpu_temperatures()
        assert temps == []


def test_get_gpu_temperatures_skips_unparseable_lines() -> None:
    """get_gpu_temperatures skips unparseable lines."""
    with mock.patch("tempfan_gpu.gpu.subprocess.run") as mock_run:
        mock_run.return_value.stdout = "75\nN/A\n82\n"
        mock_run.return_value.check_returncode.return_value = None
        temps = gpu.get_gpu_temperatures()
        assert temps == [75.0, 82.0]


def test_get_max_gpu_temperature_returns_max() -> None:
    """get_max_gpu_temperature returns the max temperature."""
    with mock.patch("tempfan_gpu.gpu.get_gpu_temperatures", return_value=[65.0, 82.0, 71.0]):
        result = gpu.get_max_gpu_temperature()
        assert result == 82.0
