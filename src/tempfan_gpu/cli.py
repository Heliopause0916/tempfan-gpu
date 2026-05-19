"""Command-line interface for tempfan-gpu."""

import argparse
import sys
import time
from typing import Optional, Sequence

from tempfan_gpu import curve, gpu, pwm


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    """Parse command-line arguments.

    Args:
        argv: Argument list (defaults to ``sys.argv[1:]`` when None).

    Returns:
        An ``argparse.Namespace`` with the parsed arguments.
    """
    parser = argparse.ArgumentParser(
        description="NVIDIA GPU temperature-based fan speed controller."
    )
    parser.add_argument(
        "--pwm-device",
        required=True,
        help="PWM device path (e.g. /sys/class/hwmon/hwmon1/pwm1).",
    )
    parser.add_argument(
        "--csv",
        help="Path to a CSV file defining the temperature-to-PWM fan curve.",
        default=None,
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=5,
        help="Polling interval in seconds (default: 5).",
    )
    return parser.parse_args(argv)


def entry_point() -> None:
    """Console entry point for the ``tempfan-gpu`` command.

    Parses arguments, loads the fan curve, enables manual PWM mode,
    and enters the main control loop.
    """
    args = parse_args()

    # Validate PWM device path
    pwm_device_path = pwm.resolve_pwm_device(args.pwm_device)

    # Load fan curve from CSV or use default
    if args.csv:
        fan_curve = curve.parse_csv_curve(args.csv)
    else:
        fan_curve = curve.make_default_curve()

    # Enable manual PWM mode
    pwm.set_pwm_manual_mode(pwm_device_path)

    print(
        f"tempfan-gpu: monitoring GPU temperature every {args.interval}s "
        f"on device {pwm_device_path}"
    )
    print(f"            curve points: {fan_curve}")

    # Main control loop
    while True:
        max_temp = gpu.get_max_gpu_temperature()
        if max_temp is not None:
            pwm_value = curve.interpolate_pwm(max_temp, fan_curve)
            pwm.set_pwm_value(pwm_device_path, pwm_value)
            print(
                f"temp={max_temp:.1f}°C -> pwm={pwm_value} "
                f"(device={pwm_device_path})"
            )
        else:
            print(
                "Warning: unable to read GPU temperature. "
                "Is nvidia-smi available?",
                file=sys.stderr,
            )
        time.sleep(args.interval)
