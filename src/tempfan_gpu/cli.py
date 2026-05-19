"""Command-line interface for tempfan-gpu."""

import argparse
import os
import signal
import sys
import time
from typing import Optional, Sequence

from loguru import logger

from tempfan_gpu import curve, gpu, pwm


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
        help="Use a built-in fan curve preset (quiet, balanced, performance).",
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=5,
        help="Polling interval in seconds (default: 5).",
    )
    parser.add_argument(
        "--plot",
        type=str,
        default=None,
        metavar="CSV_FILE",
        help="Plot a fan curve CSV and exit (requires matplotlib).",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        metavar="PNG_FILE",
        help="Output path for the plot image (required with --plot).",
    )
    args = parser.parse_args(argv)

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

    # If --plot is specified, plot the curve and exit
    if args.plot:
        try:
            from tempfan_gpu.plot import plot_curve
        except ImportError:
            logger.error("matplotlib is required for plotting. Install with: pip install tempfan-gpu[plot]")
            sys.exit(1)
        if not args.output:
            logger.error("--output is required when using --plot")
            sys.exit(1)
        plot_curve(args.plot, args.output)
        logger.info("Plot saved to {}", args.output)
        sys.exit(0)

    # Validate PWM device path
    pwm_device_path = pwm.resolve_pwm_device(args.pwm_device)
    _pwm_device_path_global = pwm_device_path

    # Acquire exclusive lock on the PWM device
    pwm.lock_pwm_device(pwm_device_path)

    # Load fan curve from CSV, preset, or use default
    if args.csv_preset:
        preset_path = os.path.join(os.path.dirname(__file__), "presets", f"{args.csv_preset}.csv")
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
            if max_temp is not None:
                pwm_value = curve.interpolate_pwm(max_temp, fan_curve)
                pwm.set_pwm_value(pwm_device_path, pwm_value)
                logger.info(
                    "temp={:.1f}°C -> pwm={} (device={})",
                    max_temp,
                    pwm_value,
                    pwm_device_path,
                )
            else:
                logger.warning(
                    "Unable to read GPU temperature. Is nvidia-smi available?"
                )
            time.sleep(args.interval)
    except KeyboardInterrupt:
        logger.info("KeyboardInterrupt received, shutting down gracefully...")
    finally:
        pwm.set_pwm_auto_mode(pwm_device_path)
        _pwm_device_path_global = None
