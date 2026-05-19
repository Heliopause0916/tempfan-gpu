"""Tests for the tempfan_gpu.pwm module."""

import os
import tempfile
from unittest import mock

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


def test_set_pwm_value_writes_clamped_value() -> None:
    """set_pwm_value writes the clamped value to the device file."""
    with tempfile.NamedTemporaryFile(mode="w+", delete=False) as f:
        path = f.name
    try:
        pwm.set_pwm_value(path, 128)
        with open(path, "r") as f:
            assert f.read().strip() == "128"

        # Clamp below 0
        pwm.set_pwm_value(path, -10)
        with open(path, "r") as f:
            assert f.read().strip() == "0"

        # Clamp above 255
        pwm.set_pwm_value(path, 300)
        with open(path, "r") as f:
            assert f.read().strip() == "255"
    finally:
        os.unlink(path)


def test_set_pwm_value_permission_error() -> None:
    """set_pwm_value raises SystemExit on PermissionError."""
    import sys
    from loguru import logger

    logger.remove()
    try:
        with mock.patch("builtins.open", mock.mock_open()) as m:
            m.side_effect = PermissionError
            try:
                pwm.set_pwm_value("/fake/pwm", 100)
                assert False, "Expected SystemExit"
            except SystemExit:
                pass
    finally:
        logger.add(sys.stderr, format="{message}", level="INFO")


def test_set_pwm_value_file_not_found() -> None:
    """set_pwm_value raises SystemExit on FileNotFoundError."""
    import sys
    from loguru import logger

    logger.remove()
    try:
        pwm.set_pwm_value("/nonexistent/pwm", 100)
        assert False, "Expected SystemExit"
    except SystemExit:
        pass
    finally:
        logger.add(sys.stderr, format="{message}", level="INFO")


def test_set_pwm_manual_mode_writes_one() -> None:
    """set_pwm_manual_mode writes '1' to the enable file."""
    with tempfile.NamedTemporaryFile(mode="w+", delete=False) as f:
        path = f.name
    enable_path = path + "_enable"
    try:
        with open(enable_path, "w") as ef:
            ef.write("0\n")
        pwm.set_pwm_manual_mode(path)
        with open(enable_path, "r") as ef:
            assert ef.read().strip() == "1"
    finally:
        if os.path.exists(enable_path):
            os.unlink(enable_path)
        os.unlink(path)


def test_set_pwm_auto_mode_writes_zero() -> None:
    """set_pwm_auto_mode writes '0' to the enable file."""
    with tempfile.NamedTemporaryFile(mode="w+", delete=False) as f:
        path = f.name
    enable_path = path + "_enable"
    try:
        with open(enable_path, "w") as ef:
            ef.write("1\n")
        pwm.set_pwm_auto_mode(path)
        with open(enable_path, "r") as ef:
            assert ef.read().strip() == "0"
    finally:
        if os.path.exists(enable_path):
            os.unlink(enable_path)
        os.unlink(path)
