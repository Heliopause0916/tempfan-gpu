"""Temperature-to-PWM curve parsing and interpolation utilities."""

import csv
from typing import List, Tuple

import numpy as np


def parse_csv_curve(csv_path: str) -> List[Tuple[float, int]]:
    """Parse a CSV fan curve file into a list of (temperature, pwm) points.

    The CSV must have two columns: temperature (°C) and PWM value (0-255).
    Validation rules:
      - At least 2 data points are required.
      - Temperature values must be non-decreasing.
      - PWM values must be non-decreasing.
      - PWM values must be in [0, 255].

    Args:
        csv_path: Path to the CSV file.

    Returns:
        A list of (temperature, pwm) tuples, sorted by temperature with
        duplicates removed (last entry wins for a given temperature).

    Raises:
        ValueError: If the CSV data fails validation.
    """
    points: List[Tuple[float, int]] = []

    with open(csv_path, "r", newline="", encoding="utf-8-sig") as f:
        reader = csv.reader(f)
        for row in reader:
            # Skip empty rows
            if not row:
                continue
            if len(row) < 2:
                raise ValueError(
                    f"Each row must have at least 2 columns, got {len(row)}: {row}"
                )
            try:
                temp = float(row[0].strip())
                if not np.isfinite(temp):
                    raise ValueError(f"Temperature must be a finite number, got: {row[0]}")
                pwm = int(row[1].strip())
            except (ValueError, TypeError) as exc:
                raise ValueError(f"Failed to parse row: {row}") from exc
            points.append((temp, pwm))

    if len(points) < 2:
        raise ValueError(
            f"At least 2 data points are required, got {len(points)}"
        )

    # Validate non-decreasing temperature (check original input order)
    temps_arr = np.array([p[0] for p in points], dtype=float)
    if np.any(np.diff(temps_arr) < 0):
        raise ValueError(
            "Temperatures must be non-decreasing in the CSV file; "
            "found a decrease in the sequence."
        )

    # Sort by temperature; for equal temperatures keep the last occurrence
    points.sort(key=lambda p: p[0])
    dedup: List[Tuple[float, int]] = []
    for p in points:
        if dedup and dedup[-1][0] == p[0]:
            dedup[-1] = p  # replace with later entry
        else:
            dedup.append(p)
    points = dedup

    # Validate non-decreasing PWM using numpy
    pwms_arr = np.array([p[1] for p in points], dtype=int)
    if np.any(np.diff(pwms_arr) < 0):
        raise ValueError(
            "PWM values must be non-decreasing; found a decrease in the sequence."
        )

    # Validate PWM range
    if np.any((pwms_arr < 0) | (pwms_arr > 255)):
        raise ValueError(
            f"PWM value out of range [0, 255] found in curve."
        )

    return points


def make_default_curve() -> List[Tuple[float, int]]:
    """Return a simple linear default fan curve (0% at 0°C, 100% at 100°C).

    Returns:
        A list containing [(0.0, 0), (100.0, 255)].
    """
    return [(0.0, 0), (100.0, 255)]


def interpolate_pwm(
    temperature: float, curve: List[Tuple[float, int]]
) -> int:
    """Interpolate a PWM value for the given temperature using numpy.interp.

    - Below the lowest curve temperature, clamps to the lowest PWM value.
    - Above the highest curve temperature, clamps to the highest PWM value.
    - Within the curve range, performs linear interpolation and rounds.

    Args:
        temperature: The GPU temperature in °C.
        curve: A list of (temperature, pwm) points sorted by temperature.

    Returns:
        An integer PWM value in [0, 255].
    """
    if not curve:
        return 0

    temps = np.array([p[0] for p in curve], dtype=float)
    pwms = np.array([p[1] for p in curve], dtype=float)

    # numpy.interp handles clamping and linear interpolation natively
    result = float(np.interp(temperature, temps, pwms))
    return round(result)
