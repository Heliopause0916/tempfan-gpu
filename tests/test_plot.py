"""Tests for the tempfan_gpu.plot module (requires matplotlib)."""

import os
import tempfile

import pytest

from tempfan_gpu import curve


@pytest.mark.skipif(
    not os.environ.get("TEMPFAN_TEST_PLOT"),
    reason="Skipped by default; set TEMPFAN_TEST_PLOT=1 to enable (requires matplotlib).",
)
def test_plot_creates_png() -> None:
    """plot_curve should produce a valid PNG file."""
    from tempfan_gpu.plot import plot_curve

    # Create a temporary CSV
    csv_content = "30.0,0\n50.0,128\n70.0,255\n"
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".csv", delete=False, encoding="utf-8"
    ) as f:
        f.write(csv_content)
        csv_path = f.name

    png_path = csv_path + ".png"
    try:
        plot_curve(csv_path, png_path)
        assert os.path.isfile(png_path)
        assert os.path.getsize(png_path) > 0
    finally:
        if os.path.isfile(csv_path):
            os.unlink(csv_path)
        if os.path.isfile(png_path):
            os.unlink(png_path)
