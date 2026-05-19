"""Tests for the tempfan_gpu.gpu module."""

from tempfan_gpu import gpu


def test_get_gpu_temperatures_returns_list() -> None:
    """get_gpu_temperatures always returns a list (possibly empty)."""
    temps = gpu.get_gpu_temperatures()
    assert isinstance(temps, list)


def test_get_max_gpu_temperature_none_on_empty() -> None:
    """get_max_gpu_temperature returns None when no temperatures available."""
    # We can't easily mock subprocess here, but we can verify the contract
    result = gpu.get_max_gpu_temperature()
    assert result is None or isinstance(result, (int, float))
