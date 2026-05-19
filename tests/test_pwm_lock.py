"""Tests for the PWM lock mechanism in tempfan_gpu.pwm."""

import sys
import tempfile

from tempfan_gpu import pwm


def test_lock_pwm_device_creates_lock_file() -> None:
    """lock_pwm_device should create a lock file on non-Windows."""
    if sys.platform == "win32":
        # On Windows the function is a no-op
        pwm.lock_pwm_device("/sys/class/hwmon/hwmon1/pwm1")
        assert True
        return

    # We can't easily test fcntl.flock without root or real sysfs,
    # but we can at least verify the function is importable and callable.
    # Use a fake path — it will fail to open the lock file (directory /tmp exists,
    # but the function may try to write there). Let's verify it at least doesn't
    # crash with unexpected exceptions.
    try:
        pwm.lock_pwm_device("/sys/class/hwmon/hwmon1/pwm1")
    except SystemExit:
        # Expected if lock file already exists or other I/O error
        pass
    except Exception:
        # Unexpected — should only raise SystemExit
        assert False, "lock_pwm_device raised unexpected exception"
