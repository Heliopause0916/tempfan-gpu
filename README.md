# tempfan-gpu

A Linux command-line tool that dynamically controls NVIDIA GPU fan PWM duty cycle based on GPU temperature.

## Features

- **Temperature-based fan control** — Monitor GPU temperatures and automatically adjust fan speed
- **Custom fan curves** — Define your own temperature-to-PWM curves via CSV files
- **Built-in presets** — Choose from quiet, balanced, or performance presets
- **Multiple GPU support** — Controls the hottest GPU among all detected NVIDIA GPUs
- **Visualize curves** — Plot fan curves as PNG images (optional matplotlib dependency)
- **Safe exit** — Automatically restores automatic fan control on SIGINT/SIGTERM
- **Device locking** — Prevents multiple instances from controlling the same PWM device

## Installation

```bash
git clone https://github.com/Heliopause0916/tempfan-gpu.git
cd tempfan-gpu
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
# Optional: install with plot support
pip install -e ".[plot]"
```

## Usage

### Runtime Mode

```bash
# Default curve: linear 0-255 from 0C to 100C
sudo tempfan-gpu --pwm-device /sys/class/hwmon/hwmon1/pwm1

# Custom CSV curve
sudo tempfan-gpu --pwm-device /sys/class/hwmon/hwmon1/pwm1 --csv my-curve.csv

# Built-in preset
sudo tempfan-gpu --pwm-device /sys/class/hwmon/hwmon1/pwm1 --csv-preset balanced

# Custom polling interval
sudo tempfan-gpu --pwm-device /sys/class/hwmon/hwmon1/pwm1 --interval 10
```

### Plot Mode (No root / --pwm-device required)

```bash
# Plot a custom CSV curve
tempfan-gpu plot --csv my-curve.csv --output curve.png

# Plot with custom temperature range
tempfan-gpu plot --csv my-curve.csv --temp-min 0 --temp-max 90 --output curve.png

# Plot a built-in preset
tempfan-gpu plot --csv-preset balanced --output curve.png

# List available presets (by passing an invalid preset name)
tempfan-gpu --csv-preset invalid
```

## Find Your PWM Device

```bash
ls /sys/class/hwmon/
ls /sys/class/hwmon/hwmon*/pwm*
cat /sys/class/hwmon/hwmon*/name
```

## systemd Service

Create `/etc/systemd/system/tempfan-gpu.service`:

```ini
[Unit]
Description=GPU Temperature-Based Fan Controller
After=multi-user.target

[Service]
Type=simple
ExecStart=/opt/tempfan-gpu/.venv/bin/tempfan-gpu \
    --pwm-device /sys/class/hwmon/hwmon1/pwm1 \
    --csv-preset balanced
Restart=always
RestartSec=5
User=root

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable tempfan-gpu
sudo systemctl start tempfan-gpu
sudo systemctl status tempfan-gpu
sudo journalctl -u tempfan-gpu -f
```

For multi-fan setups, create separate service files with different `--pwm-device` paths.

## Fan Curve CSV Format

```csv
temperature_C,PWM
30,50
50,100
70,180
85,255
```

Rules:
- **Encoding**: utf-8-sig (BOM-compatible)
- **Columns**: temperature (C), PWM (0-255)
- **Minimum**: at least 2 data points
- **Order**: both temperature and PWM must be non-decreasing (equal values allowed)
- **PWM range**: [0, 255]
- **Interpolation**: linear via `numpy.interp`, results `round()` to integer
- **Clamping**: below the first point → first PWM; above the last point → last PWM

> Note: `numpy.interp(50.0, [0.0, 100.0], [0, 255])` → `127.5` → `round()` → `127` (not 128)

## Built-in Presets

| Preset        | Description       | Start (PWM=0) | Full Speed (PWM=255) | 50°C PWM | Curve Characteristics          |
|---------------|-------------------|---------------|----------------------|----------|--------------------------------|
| quiet         | Silence priority  | 30°C          | 85°C                 | 64       | Gradual ramp, low noise        |
| balanced      | Moderate slope    | 30°C          | 85°C                 | 64       | Balanced heat-noise trade-off  |
| performance   | Early ramp-up     | 20°C          | 70°C                 | 102      | Aggressive cooling early on    |

## Arguments

### Runtime Mode (`tempfan-gpu`)

| Argument        | Description                                | Required            |
|-----------------|--------------------------------------------|---------------------|
| `--pwm-device`  | PWM device path                            | Yes                 |
| `--csv`         | Custom fan curve CSV file                  | No (mutex with --csv-preset) |
| `--csv-preset`  | Built-in preset (quiet/balanced/performance)| No (mutex with --csv) |
| `--interval`    | Polling interval in seconds (default: 5)   | No                  |

Default curve (no `--csv` / `--csv-preset`): linear 0-255 from 0°C to 100°C.

### Plot Subcommand (`tempfan-gpu plot`)

| Argument        | Description                                | Required            |
|-----------------|--------------------------------------------|---------------------|
| `--csv`         | Custom fan curve CSV file                  | No (mutex with --csv-preset) |
| `--csv-preset`  | Built-in preset (quiet/balanced/performance)| No (mutex with --csv) |
| `--output`      | Output PNG file path                       | Yes                 |
| `--temp-min`    | Minimum temperature for X-axis (default: 0)| No                  |
| `--temp-max`    | Maximum temperature for X-axis (default: 120)| No                 |

## NaN/Inf Temperature Protection

The tool handles sensor anomalies gracefully:

- **`gpu.py`**: Parsed temperature values from `nvidia-smi` are filtered through `math.isfinite()`, rejecting NaN, Inf, and -Inf.
- **`cli.py`**: The main loop applies a secondary `math.isfinite()` check as defense-in-depth.
- **`curve.py`**: CSV temperature values are validated with `np.isfinite()` during parsing.
- On invalid temperature readings, the controller logs a warning and skips the cycle without crashing.

## Device Locking

Uses `fcntl.flock` on `/tmp/tempfan-{device}.lock` to prevent multiple instances
from controlling the same PWM device. Lock auto-releases on process exit.
Windows is a no-op (lock file not created).

## Requirements

- **OS**: Linux only
- **GPU**: NVIDIA GPU with `nvidia-smi`
- **Permissions**: root for sysfs writes
- **Python**: >= 3.8

**Dependencies**: numpy, loguru (required); matplotlib (optional, for `plot` subcommand)

## Development

```bash
source .venv/bin/activate
pip install -e ".[plot]"
python -m pytest tests/ -v
```

### Testing Notes

- Tests use `tempfile.NamedTemporaryFile` for temp CSV creation; cleaned with `os.unlink`.
- `test_plot` is skipped by default; set `TEMPFAN_TEST_PLOT=1` to enable (requires matplotlib).
- No external services or network access required.
- `test_gpu` verifies type contracts; returns `None` when no NVIDIA GPU is present.

## Project Structure

```
src/tempfan_gpu/
  __main__.py         # python -m tempfan_gpu entry
  cli.py              # CLI parsing, signal handling, main loop
  curve.py            # CSV parsing, validation, numpy interpolation
  gpu.py              # nvidia-smi temperature query
  pwm.py              # sysfs PWM operations + device locking
  plot.py             # matplotlib plotting (optional, plot subcommand)
  presets/            # Built-in CSV presets
    quiet.csv
    balanced.csv
    performance.csv
tests/                # pytest tests
  test_curve.py
  test_gpu.py
  test_pwm.py
  test_pwm_lock.py
  test_presets.py
  test_plot.py        # skipped by default
```

## Exit Safety

On SIGINT/SIGTERM or normal exit, the tool automatically writes `0` to `pwmX_enable`
to restore automatic fan control. This is guaranteed through:

1. **Signal handlers**: `signal.signal()` captures SIGINT/SIGTERM.
2. **`try/finally`**: The main loop's `finally` block runs `set_pwm_auto_mode()`.
3. **`atexit`**: Lock files are released at process exit.

No fan hardware is left in manual mode if the tool exits unexpectedly.

## License

MIT
