"""PWM device file operations for GPU fan control."""

import sys

from loguru import logger

# Lock file tracking (only used on non-Windows platforms)
_locked_devices_fds: dict = {}
_atexit_registered: bool = False


def _release_all_locks() -> None:
    """Release all acquired PWM device locks on process exit."""
    import fcntl

    for fd in _locked_devices_fds.values():
        try:
            fcntl.flock(fd, fcntl.LOCK_UN)
            fd.close()
        except Exception:
            pass


def lock_pwm_device(pwm_device_path: str) -> None:
    """Acquire an exclusive lock on the PWM device.

    Creates a lock file at /tmp/tempfan-{basename}.lock using fcntl.flock.
    If another instance holds the lock, exits with an error message.

    The lock is automatically released when the process exits (flock semantics).

    On Windows, this function is a no-op.

    Args:
        pwm_device_path: The PWM device path (e.g. /sys/class/hwmon/hwmon1/pwm1).

    Raises:
        SystemExit: If the lock cannot be acquired.
    """
    if sys.platform == "win32":
        return  # Skip locking on Windows

    import atexit
    import fcntl
    import os

    # Register cleanup at module level only once to avoid stacking
    global _atexit_registered
    if not _atexit_registered:
        atexit.register(_release_all_locks)
        _atexit_registered = True

    device_name = os.path.basename(pwm_device_path)  # e.g. "pwm1"
    lock_path = f"/tmp/tempfan-{device_name}.lock"

    try:
        lock_fd = open(lock_path, "w")
        fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        # Store fd so it stays alive for the process lifetime
        _locked_devices_fds[device_name] = lock_fd
        logger.debug("Acquired lock on {}", pwm_device_path)
    except (IOError, OSError):
        logger.error(
            "Failed to acquire lock on {}. Another tempfan-gpu instance may be controlling this device.",
            pwm_device_path,
        )
        logger.error("If sure no other instance is running, remove {} manually.", lock_path)
        sys.exit(1)


def resolve_pwm_device(pwm_device: str) -> str:
    """Validate and return the PWM device path from CLI argument.

    Args:
        pwm_device: The PWM device path from the ``--pwm-device`` CLI argument.

    Returns:
        The PWM device path string.

    Raises:
        SystemExit: If the path is empty or None.
    """
    if not pwm_device:
        logger.error("PWM device not specified. Use --pwm-device to specify the device path.")
        sys.exit(1)

    return pwm_device


def _write_pwm_enable(pwm_device_path: str, value: str) -> None:
    """Write a value to the ``pwmX_enable`` file.

    Args:
        pwm_device_path: The base PWM device path.
        value: ``"1"`` for manual mode, ``"0"`` for automatic mode.

    Raises:
        SystemExit: If a file error occurs.
    """
    enable_path = pwm_device_path + "_enable"
    try:
        with open(enable_path, "w", encoding="utf-8") as f:
            f.write(f"{value}\n")
    except PermissionError:
        logger.error(f"Permission denied when writing to {enable_path}. Try running as root (e.g. sudo).")
        sys.exit(1)
    except FileNotFoundError:
        logger.error(f"PWM enable file not found: {enable_path}. Check the device path.")
        sys.exit(1)
    except OSError as exc:
        logger.error(f"OS error when writing to {enable_path}: {exc}")
        sys.exit(1)


def set_pwm_manual_mode(pwm_device_path: str) -> None:
    """Switch the PWM fan controller to manual mode.

    Writes ``"1\n"`` to ``{pwm_device_path}_enable`` to enable manual fan
    control (disables automatic temperature-based fan control).

    Args:
        pwm_device_path: The base PWM device path (e.g. ``/sys/class/hwmon/...``).
    """
    _write_pwm_enable(pwm_device_path, "1")
    logger.info("Manual PWM mode enabled on {}", pwm_device_path)


def set_pwm_auto_mode(pwm_device_path: str) -> None:
    """Restore automatic PWM fan control mode.

    Writes ``"0\n"`` to ``{pwm_device_path}_enable`` to give back control
    to the hardware automatic fan controller.

    Args:
        pwm_device_path: The base PWM device path.
    """
    _write_pwm_enable(pwm_device_path, "0")
    logger.info("Automatic PWM mode restored on {}", pwm_device_path)


def set_pwm_value(pwm_device_path: str, value: int) -> None:
    """Write a PWM value to the fan device.

    The value is clamped to the range [0, 255] before writing.

    Args:
        pwm_device_path: The PWM device file path.
        value: The desired PWM duty cycle (0-255).

    Raises:
        SystemExit: If a file error occurs.
    """
    clamped = max(0, min(255, value))
    try:
        with open(pwm_device_path, "w", encoding="utf-8") as f:
            f.write(f"{clamped}\n")
    except PermissionError:
        logger.error(f"Permission denied when writing to {pwm_device_path}. Try running as root (e.g. sudo).")
        sys.exit(1)
    except FileNotFoundError:
        logger.error(f"PWM device file not found: {pwm_device_path}. Check the device path.")
        sys.exit(1)
    except OSError as exc:
        logger.error(f"OS error when writing to {pwm_device_path}: {exc}")
        sys.exit(1)
