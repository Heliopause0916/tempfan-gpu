"""Tests for built-in CSV preset curves."""

import os

from tempfan_gpu import curve


def _preset_path(name: str) -> str:
    """Return the filesystem path to a built-in preset CSV."""
    return os.path.join(
        os.path.dirname(os.path.dirname(__file__)),
        "src",
        "tempfan_gpu",
        "presets",
        f"{name}.csv",
    )


def test_preset_quiet() -> None:
    """quiet preset is parseable and obeys curve constraints."""
    points = curve.parse_csv_curve(_preset_path("quiet"))
    assert len(points) >= 2


def test_preset_balanced() -> None:
    """balanced preset is parseable and obeys curve constraints."""
    points = curve.parse_csv_curve(_preset_path("balanced"))
    assert len(points) >= 2


def test_preset_performance() -> None:
    """performance preset is parseable and obeys curve constraints."""
    points = curve.parse_csv_curve(_preset_path("performance"))
    assert len(points) >= 2
