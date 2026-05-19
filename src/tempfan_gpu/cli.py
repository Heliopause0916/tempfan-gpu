"""Command-line interface for tempfan-gpu."""

import argparse
import math
import os
import signal
import sys
import time
from typing import Optional, Sequence

from loguru import logger

from tempfan_gpu import curve, gpu, pwm

_PRESETS_DIR = os.path.join(os.path.dirname(__file__), "presets")


def _list_available_presets() -> list[str]:
    """Return sorted list of available preset names (without .csv extension)."""
    presets = []
    if os.path.isdir(_PRESETS_DIR):
        for fname in os.listdir(_PRESETS_DIR):
            if fname.endswith(".csv"):
                presets.append(fname[:-4])
    return sorted(presets)


# Global reference to PWM device path for signal handler cleanup
_pwm_device_path_global: Optional[str] = None


def _restore_auto_mode(signum: int, frame) -> None:
    """Signal handler: restore automatic fan control before exit.

    Registered for SIGINT and SIGTERM. Writes ``0`` to the ``pwmX_enable``
    file so the hardware regains automatic fan control.
    """
    if _pwm_device_path_global is not None:
        logger.warning("Received signal {}, restoring automatic fan control...", signum)
        pwm.set_pwm_auto_mode(_pwm_device_path_global)
    sys.exit(0)


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
    subparsers = parser.add_subparsers(dest="command")

    # --- Top-level (run mode) arguments ---
    parser.add_argument(
        "--pwm-device",
        help="PWM device path (e.g. /sys/class/hwmon/hwmon1/pwm1).",
    )
    curve_group = parser.add_mutually_exclusive_group()
    curve_group.add_argument(
        "--csv",
        help="Path to a CSV file defining the temperature-to-PWM fan curve.",
        default=None,
    )
    curve_group.add_argument(
        "--csv-preset",
        type=str,
        default=None,
        help=f"Use a built-in fan curve preset ({', '.join(_list_available_presets())}).",
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=5,
        help="Polling interval in seconds (default: 5).",
    )

    # --- plot subcommand ---
    plot_parser = subparsers.add_parser(
        "plot",
        help="Plot a fan curve CSV and save as PNG (requires matplotlib).",
        description="Plot a temperature-to-PWM fan curve and save it as a PNG image.",
    )
    plot_curve_group = plot_parser.add_mutually_exclusive_group(required=True)
    plot_curve_group.add_argument(
        "--csv",
        help="Path to a CSV file defining the temperature-to-PWM fan curve.",
    )
    plot_curve_group.add_argument(
        "--csv-preset",
        type=str,
        help=f"Use a built-in fan curve preset ({', '.join(_list_available_presets())}).",
    )
    plot_parser.add_argument(
        "--output",
        type=str,
        required=True,
        metavar="PNG_FILE",
        help="Output path for the plot image.",
    )
    plot_parser.add_argument(
        "--temp-min",
        type=float,
        default=0.0,
        help="Minimum temperature for the x-axis in °C (default: 0).",
    )
    plot_parser.add_argument(
        "--temp-max",
        type=float,
        default=120.0,
        help="Maximum temperature for the x-axis in °C (default: 120).",
    )

    args = parser.parse_args(argv)

    if args.command is None:
        # Run mode: validate interval
        if args.interval < 1:
            parser.error(f"--interval must be a positive integer, got {args.interval}")

    return args


def entry_point() -> None:
    """Console entry point for the ``tempfan-gpu`` command.

    Parses arguments, loads the fan curve, enables manual PWM mode,
    registers signal handlers for safe exit, and enters the main
    control loop. On any exit (normal, signal, or exception) the
    automatic fan control mode is restored.
    """
    global _pwm_device_path_global

    args = parse_args()

    # --- plot subcommand ---
    if args.command == "plot":
        if args.csv_preset:
            available = _list_available_presets()
            if args.csv_preset not in available:
                logger.error(
                    "Unknown preset '{}'. Available presets: {}",
                    args.csv_preset,
                    ", ".join(available),
                )
                sys.exit(1)
            csv_path = os.path.join(_PRESETS_DIR, f"{args.csv_preset}.csv")
        else:
            csv_path = args.csv
        try:
            from tempfan_gpu.plot import plot_curve
        except ImportError:
            logger.error("matplotlib is required for plotting. Install with: pip install tempfan-gpu[plot]")
            sys.exit(1)
        plot_curve(csv_path, args.output, args.temp_min, args.temp_max)
        logger.info("Plot saved to {}", args.output)
        sys.exit(0)

    # --- Run mode ---

    # Validate PWM device path
    pwm_device_path = pwm.resolve_pwm_device(args.pwm_device)
    _pwm_device_path_global = pwm_device_path

    # Acquire exclusive lock on the PWM device
    pwm.lock_pwm_device(pwm_device_path)

    # Load fan curve from CSV, preset, or use default
    if args.csv_preset:
        available = _list_available_presets()
        if args.csv_preset not in available:
            logger.error(
                "Unknown preset '{}'. Available presets: {}",
                args.csv_preset,
                ", ".join(available),
            )
            sys.exit(1)
        preset_path = os.path.join(_PRESETS_DIR, f"{args.csv_preset}.csv")
        fan_curve = curve.parse_csv_curve(preset_path)
        logger.info("Loaded preset curve: {}", args.csv_preset)
    elif args.csv:
        fan_curve = curve.parse_csv_curve(args.csv)
    else:
        fan_curve = curve.make_default_curve()

    # Register signal handlers for graceful exit
    signal.signal(signal.SIGINT, _restore_auto_mode)
    signal.signal(signal.SIGTERM, _restore_auto_mode)

    # Enable manual PWM mode
    pwm.set_pwm_manual_mode(pwm_device_path)

    logger.info(
        "Monitoring GPU temperature every {}s on device {}",
        args.interval,
        pwm_device_path,
    )
    logger.info("Curve points: {}", fan_curve)

    try:
        # Main control loop
        while True:
            max_temp = gpu.get_max_gpu_temperature()
            if max_temp is not None and math.isfinite(max_temp):
                pwm_value = curve.interpolate_pwm(max_temp, fan_curve)
                pwm.set_pwm_value(pwm_device_path, pwm_value)
                logger.info(
                    "temp={:.1f}°C -> pwm={} (device={})",
                    max_temp,
                    pwm_value,
                    pwm_device_path,
                )
            elif max_temp is None:
                logger.warning(
                    "Unable to read GPU temperature. Is nvidia-smi available?"
                )
            else:
                logger.warning(
                    "Invalid GPU temperature ({}), skipping cycle...", max_temp
                )
            time.sleep(args.interval)
    finally:
        pwm.set_pwm_auto_mode(pwm_device_path)
        _pwm_device_path_global = None
