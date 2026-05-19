"""Tests for the tempfan_gpu.pwm module."""

from tempfan_gpu import pwm


def test_resolve_pwm_device_valid() -> None:
    """Valid PWM device path returns unchanged."""
    path = "/sys/class/hwmon/hwmon1/pwm1"
    assert pwm.resolve_pwm_device(path) == path


def test_resolve_pwm_device_empty():
    """Empty PWM device path raises SystemExit."""
    import sys
    from io import StringIO
    from loguru import logger

    # Remove default logger to suppress output during test
    logger.remove()
    try:
        pwm.resolve_pwm_device("")
        assert False, "Expected SystemExit"
    except SystemExit:
        pass
    finally:
        logger.add(sys.stderr, format="{message}", level="INFO")
