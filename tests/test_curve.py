"""Tests for the tempfan_gpu.curve module."""

import os
import tempfile

from tempfan_gpu import curve


# ── interpolate_pwm tests ──────────────────────────────────────────────


def test_default_curve() -> None:
    """Default curve should interpolate linearly: 0->0, 50->127/128, 100->255."""
    c = curve.make_default_curve()
    assert curve.interpolate_pwm(0.0, c) == 0
    assert curve.interpolate_pwm(50.0, c) == 128
    assert curve.interpolate_pwm(100.0, c) == 255


def test_below_range_clamp() -> None:
    """Temperature below the lowest curve point clamps to the lowest PWM."""
    c = [(20.0, 50), (80.0, 200)]
    assert curve.interpolate_pwm(10.0, c) == 50
    assert curve.interpolate_pwm(0.0, c) == 50
    assert curve.interpolate_pwm(-5.0, c) == 50


def test_above_range_clamp() -> None:
    """Temperature above the highest curve point clamps to the highest PWM."""
    c = [(20.0, 50), (80.0, 200)]
    assert curve.interpolate_pwm(90.0, c) == 200
    assert curve.interpolate_pwm(100.0, c) == 200
    assert curve.interpolate_pwm(200.0, c) == 200


def test_interpolate_midpoint() -> None:
    """Verify precise linear interpolation between two known points."""
    c = [(30.0, 50), (70.0, 150)]
    assert curve.interpolate_pwm(50.0, c) == 100
    assert curve.interpolate_pwm(35.0, c) == 62


# ── parse_csv_curve tests ──────────────────────────────────────────────


def test_parse_csv_valid() -> None:
    """Parse a valid CSV fan curve correctly."""
    content = (
        "0.0,0\n"
        "40.0,80\n"
        "60.0,160\n"
        "80.0,220\n"
        "100.0,255\n"
    )
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".csv", delete=False, encoding="utf-8"
    ) as f:
        f.write(content)
        tmp_path = f.name

    try:
        points = curve.parse_csv_curve(tmp_path)
        assert points == [(0.0, 0), (40.0, 80), (60.0, 160),
                          (80.0, 220), (100.0, 255)]
    finally:
        os.unlink(tmp_path)


def test_parse_csv_invalid_non_decreasing() -> None:
    """Non-decreasing temperature order must raise ValueError."""
    content = "0.0,0\n100.0,255\n50.0,100\n"
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".csv", delete=False, encoding="utf-8"
    ) as f:
        f.write(content)
        tmp_path = f.name

    try:
        curve.parse_csv_curve(tmp_path)
        assert False, "Expected ValueError for non-decreasing temperatures"
    except ValueError:
        pass
    finally:
        os.unlink(tmp_path)


def test_parse_csv_invalid_no_100_255() -> None:
    """A curve without (100, 255) as the last point must raise ValueError."""
    content = "0.0,0\n50.0,128\n90.0,200\n"
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".csv", delete=False, encoding="utf-8"
    ) as f:
        f.write(content)
        tmp_path = f.name

    try:
        curve.parse_csv_curve(tmp_path)
        assert False, "Expected ValueError for missing (100, 255)"
    except ValueError:
        pass
    finally:
        os.unlink(tmp_path)


def test_parse_csv_invalid_pwm_range() -> None:
    """PWM values outside [0, 255] must raise ValueError."""
    content = "0.0,0\n100.0,300\n"
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".csv", delete=False, encoding="utf-8"
    ) as f:
        f.write(content)
        tmp_path = f.name

    try:
        curve.parse_csv_curve(tmp_path)
        assert False, "Expected ValueError for out-of-range PWM"
    except ValueError:
        pass
    finally:
        os.unlink(tmp_path)


def test_parse_csv_empty() -> None:
    """An empty file or file with too few points must raise ValueError."""
    content = "100.0,255\n"  # only one point
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".csv", delete=False, encoding="utf-8"
    ) as f:
        f.write(content)
        tmp_path = f.name

    try:
        curve.parse_csv_curve(tmp_path)
        assert False, "Expected ValueError for insufficient points"
    except ValueError:
        pass
    finally:
        os.unlink(tmp_path)
