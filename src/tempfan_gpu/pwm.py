"""PWM device file operations for GPU fan control."""

import sys


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
        print(
            "Error: PWM device not specified. "
            "Use --pwm-device to specify the device path.",
            file=sys.stderr,
        )
        sys.exit(1)

    return pwm_device


def set_pwm_manual_mode(pwm_device_path: str) -> None:
    """Switch the PWM fan controller to manual mode.

    Writes ``"1\n"`` to ``{pwm_device_path}_enable`` to enable manual fan
    control (disables automatic temperature-based fan control).

    Args:
        pwm_device_path: The base PWM device path (e.g. ``/sys/class/hwmon/...``).

    Raises:
        SystemExit: If a ``PermissionError`` occurs (prints a friendly message).
    """
    enable_path = pwm_device_path + "_enable"
    try:
        with open(enable_path, "w", encoding="utf-8") as f:
            f.write("1\n")
    except PermissionError:
        print(
            f"Error: Permission denied when writing to {enable_path}. "
            f"Try running as root (e.g. sudo).",
            file=sys.stderr,
        )
        sys.exit(1)


def set_pwm_value(pwm_device_path: str, value: int) -> None:
    """Write a PWM value to the fan device.

    The value is clamped to the range [0, 255] before writing.

    Args:
        pwm_device_path: The PWM device file path.
        value: The desired PWM duty cycle (0-255).

    Raises:
        SystemExit: If a ``PermissionError`` occurs (prints a friendly message).
    """
    clamped = max(0, min(255, value))
    try:
        with open(pwm_device_path, "w", encoding="utf-8") as f:
            f.write(f"{clamped}\n")
    except PermissionError:
        print(
            f"Error: Permission denied when writing to {pwm_device_path}. "
            f"Try running as root (e.g. sudo).",
            file=sys.stderr,
        )
        sys.exit(1)
