"""Plot temperature-to-PWM fan curve as a PNG image."""

import numpy as np

from tempfan_gpu import curve


def plot_curve(csv_path: str, output_path: str, temp_min: float = 0.0, temp_max: float = 120.0) -> None:
    """Plot the temperature-to-PWM fan curve and save as PNG.

    Args:
        csv_path: Path to the CSV curve file.
        output_path: Path for the output PNG image.
        temp_min: Minimum temperature for the x-axis (°C, default 0).
        temp_max: Maximum temperature for the x-axis (°C, default 120).
    """
    import matplotlib.pyplot as plt

    # Parse the curve
    points = curve.parse_csv_curve(csv_path)
    temps_raw = np.array([p[0] for p in points], dtype=float)
    pwms_raw = np.array([p[1] for p in points], dtype=float)

    # Generate dense temperature range from 0 to 120°C for smooth interpolation.
    # numpy.interp clamps to boundary values outside the CSV domain, so the
    # plotted curve exactly matches runtime behavior (flat at both ends).
    num_points = max(2, int((temp_max - temp_min) * 10) + 1)
    temps_dense = np.linspace(temp_min, temp_max, num=num_points)
    pwms_dense = np.array(
        curve.interpolate_temperature(temps_dense, points), dtype=float
    )

    # Y-axis padding ratio (5% margin above and below)
    _padding = 0.05

    # Create the plot
    fig, ax1 = plt.subplots(figsize=(10, 6))

    # Primary y-axis: percentage (0-100%)
    ax1.plot(
        temps_dense, pwms_dense / 255.0 * 100.0,
        color="blue", linewidth=2, label="Fan curve",
    )
    ax1.scatter(
        temps_raw, pwms_raw / 255.0 * 100.0,
        color="red", s=60, zorder=5, label="Curve points",
    )
    ax1.set_xlabel("Temperature (°C)", fontsize=12)
    ax1.set_ylabel("Fan speed (%)", fontsize=12, color="blue")
    ax1.tick_params(axis="y", labelcolor="blue")
    ax1.set_ylim(-_padding * 100.0, (1 + _padding) * 100.0)
    ax1.grid(True, linestyle="--", alpha=0.6)

    # Secondary y-axis: PWM value (0-255)
    ax2 = ax1.twinx()
    ax2.set_ylabel("PWM value", fontsize=12, color="green")
    ax2.tick_params(axis="y", labelcolor="green")
    ax2.set_ylim(-_padding * 255.0, (1 + _padding) * 255.0)

    # Title and legend
    ax1.set_title(f"Fan Curve: {csv_path}  ({temp_min}°C – {temp_max}°C)", fontsize=14)
    fig.legend(loc="upper left", bbox_to_anchor=(0.12, 0.88))

    fig.tight_layout()
    fig.savefig(output_path, dpi=150)
    plt.close(fig)
