"""Temperature-to-PWM curve parsing and interpolation utilities."""

import csv
from typing import List, Tuple


def parse_csv_curve(csv_path: str) -> List[Tuple[float, int]]:
    """Parse a CSV fan curve file into a list of (temperature, pwm) points.

    The CSV must have two columns: temperature (°C) and PWM value (0-255).
    Validation rules:
      - At least 2 data points are required.
      - Temperature values must be non-decreasing.
      - PWM values must be non-decreasing.
      - PWM values must be in [0, 255].
      - The last point must be (100, 255).

    Args:
        csv_path: Path to the CSV file.

    Returns:
        A list of (temperature, pwm) tuples, sorted by temperature with
        duplicates removed (last entry wins for a given temperature).

    Raises:
        ValueError: If the CSV data fails validation.
    """
    points: List[Tuple[float, int]] = []

    with open(csv_path, "r", newline="", encoding="utf-8") as f:
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
                pwm = int(row[1].strip())
            except (ValueError, TypeError) as exc:
                raise ValueError(f"Failed to parse row: {row}") from exc
            points.append((temp, pwm))

    if len(points) < 2:
        raise ValueError(
            f"At least 2 data points are required, got {len(points)}"
        )

    # Validate non-decreasing temperature (check original input order)
    for i in range(1, len(points)):
        if points[i][0] < points[i - 1][0]:
            raise ValueError(
                f"Temperatures must be non-decreasing in the CSV file; "
                f"found {points[i - 1][0]} followed by {points[i][0]}"
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

    # Validate non-decreasing PWM
    for i in range(1, len(points)):
        if points[i][1] < points[i - 1][1]:
            raise ValueError(
                f"PWM values must be non-decreasing; found {points[i - 1][1]} "
                f"followed by {points[i][1]}"
            )

    # Validate PWM range
    for temp, pwm in points:
        if not (0 <= pwm <= 255):
            raise ValueError(
                f"PWM value {pwm} at temperature {temp} is out of range [0, 255]"
            )

    # Validate last point is (100, 255)
    last_temp, last_pwm = points[-1]
    if last_temp != 100.0 or last_pwm != 255:
        raise ValueError(
            f"The last curve point must be (100, 255), got ({last_temp}, {last_pwm})"
        )

    return points


def make_default_curve() -> List[Tuple[float, int]]:
    """Return a simple linear default fan curve.

    Returns:
        A list containing [(0.0, 0), (100.0, 255)].
    """
    return [(0.0, 0), (100.0, 255)]


def interpolate_pwm(
    temperature: float, curve: List[Tuple[float, int]]
) -> int:
    """Interpolate a PWM value for the given temperature using the curve.

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

    # Below minimum temperature → clamp to lowest PWM
    if temperature <= curve[0][0]:
        return curve[0][1]

    # Above maximum temperature → clamp to highest PWM
    if temperature >= curve[-1][0]:
        return curve[-1][1]

    # Find the segment containing the temperature
    for i in range(1, len(curve)):
        t_low, pwm_low = curve[i - 1]
        t_high, pwm_high = curve[i]

        if t_low <= temperature <= t_high:
            # Linear interpolation
            if t_high == t_low:
                # Division-by-zero guard: return the nearest PWM
                return pwm_low
            ratio = (temperature - t_low) / (t_high - t_low)
            interpolated = pwm_low + ratio * (pwm_high - pwm_low)
            return round(interpolated)

    # Fallback (should not be reached)
    return curve[-1][1]
