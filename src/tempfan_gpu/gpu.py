"""GPU temperature querying via nvidia-smi."""

import subprocess
from typing import List, Optional


def get_gpu_temperatures() -> List[float]:
    """Query all NVIDIA GPU temperatures using nvidia-smi.

    Runs::

        nvidia-smi --query-gpu=temperature.gpu --format=csv,noheader,nounits

    Returns:
        A list of GPU temperature values in °C. Returns an empty list on
        any error (e.g. nvidia-smi not found, process timeout, parse failure).
    """
    try:
        result = subprocess.run(
            [
                "nvidia-smi",
                "--query-gpu=temperature.gpu",
                "--format=csv,noheader,nounits",
            ],
            capture_output=True,
            text=True,
            timeout=10,
        )
        result.check_returncode()
    except (FileNotFoundError, subprocess.CalledProcessError,
            subprocess.TimeoutExpired):
        return []

    temperatures: List[float] = []
    for line in result.stdout.strip().splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            temperatures.append(float(line))
        except ValueError:
            # Skip unparseable lines
            continue

    return temperatures


def get_max_gpu_temperature() -> Optional[float]:
    """Return the maximum temperature among all detected NVIDIA GPUs.

    Returns:
        The highest GPU temperature in °C, or None if no GPU data is available.
    """
    temps = get_gpu_temperatures()
    if not temps:
        return None
    return max(temps)
