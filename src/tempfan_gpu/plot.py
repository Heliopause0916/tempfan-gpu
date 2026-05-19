"""Plot temperature-to-PWM fan curve as a PNG image."""

import numpy as np

from tempfan_gpu import curve


def plot_curve(csv_path: str, output_path: str) -> None:
    """Plot the temperature-to-PWM fan curve and save as PNG.

    Args:
        csv_path: Path to the CSV curve file.
        output_path: Path for the output PNG image.
    """
    import matplotlib.pyplot as plt

    # Parse the curve
    points = curve.parse_csv_curve(csv_path)
    temps_raw = np.array([p[0] for p in points], dtype=float)
    pwms_raw = np.array([p[1] for p in points], dtype=float)

    # Generate dense temperature range for smooth interpolation
    temp_min = float(np.min(temps_raw))
    temp_max = float(np.max(temps_raw))
    temps_dense = np.arange(temp_min, temp_max + 1.0, 1.0)
    pwms_dense = np.array(
        [curve.interpolate_pwm(t, points) for t in temps_dense], dtype=float
    )

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
    pwm_max_raw = float(np.max(pwms_raw))
    ax1.set_ylim(0, pwm_max_raw / 255.0 * 100.0 + 5)
    ax1.grid(True, linestyle="--", alpha=0.6)

    # Secondary y-axis: PWM value (0-255)
    ax2 = ax1.twinx()
    ax2.set_ylabel("PWM value", fontsize=12, color="green")
    ax2.tick_params(axis="y", labelcolor="green")
    ax2.set_ylim(0, pwm_max_raw + 5)

    # Title and legend
    ax1.set_title(f"Fan Curve: {csv_path}", fontsize=14)
    fig.legend(loc="upper left", bbox_to_anchor=(0.12, 0.88))

    fig.tight_layout()
    fig.savefig(output_path, dpi=150)
    plt.close(fig)
