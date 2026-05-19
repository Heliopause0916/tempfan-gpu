# tempfan-gpu

A Linux command-line tool that dynamically controls NVIDIA GPU fan PWM duty cycle based on GPU temperature.

## Features

- Temperature-based fan control - Monitor GPU temperatures and automatically adjust fan speed
- Custom fan curves - Define your own temperature-to-PWM curves via CSV files
- Built-in presets - Choose from quiet, balanced, or performance presets
- Multiple GPU support - Controls the hottest GPU among all detected NVIDIA GPUs
- Visualize curves - Plot fan curves as PNG images (optional matplotlib dependency)
- Safe exit - Automatically restores automatic fan control on SIGINT/SIGTERM
- Device locking - Prevents multiple instances from controlling the same PWM device

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

```bash
# Default curve: linear 0-255 from 0C to 100C
sudo tempfan-gpu --pwm-device /sys/class/hwmon/hwmon1/pwm1

# Custom CSV curve
sudo tempfan-gpu --pwm-device /sys/class/hwmon/hwmon1/pwm1 --csv my-curve.csv

# Built-in preset
sudo tempfan-gpu --pwm-device /sys/class/hwmon/hwmon1/pwm1 --csv-preset balanced

# Custom polling interval
sudo tempfan-gpu --pwm-device /sys/class/hwmon/hwmon1/pwm1 --interval 10

# Plot a fan curve (requires matplotlib, no --pwm-device needed)
tempfan-gpu --plot my-curve.csv --output curve.png
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

For multi-fan setups, create separate service files with different --pwm-device paths.

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
- **Interpolation**: linear via numpy.interp, results round() to integer
- **Clamping**: below the first point -> first PWM; above the last point -> last PWM

Important: numpy.interp(50.0, [0.0, 100.0], [0, 255]) -> 127.5 -> round() -> 127 (not 128)

## Built-in Presets

| Preset        | Description                 | Curve                  |
|---------------|-----------------------------|------------------------|
| quiet         | Silent priority             | 30C/0% ~ 85C/100%     |
| balanced      | Moderate slope              | 30C/0% ~ 85C/100%     |
| performance   | Early ramp-up               | 20C/0% ~ 70C/100%     |

## Arguments

| Argument        | Description                                   | Required             |
|----------------|-----------------------------------------------|----------------------|
| --pwm-device   | PWM device path                               | Yes (runtime mode)   |
| --csv          | Custom fan curve CSV file                     | No*                  |
| --csv-preset   | Built-in preset                               | No*                  |
| --interval     | Polling interval in seconds (default: 5)      | No                   |
| --plot         | Plot a CSV curve and exit                     | No                   |
| --output       | Output PNG path for --plot                    | Yes (with --plot)    |

* --csv and --csv-preset are mutually exclusive. Default: linear 0-255 from 0C to 100C.

## Device Locking

Uses fcntl.flock on /tmp/tempfan-{device}.lock to prevent multiple instances
from controlling the same PWM device. Lock auto-releases on process exit.

## Requirements

- OS: Linux only
- GPU: NVIDIA GPU with nvidia-smi
- Permissions: root for sysfs writes
- Python: >= 3.8

Dependencies: numpy, loguru (required); matplotlib (optional for --plot)

## Development

```bash
source .venv/bin/activate
pip install -e ".[plot]"
python -m pytest tests/ -v
```

## Project Structure

```
src/tempfan_gpu/
  __main__.py         # python -m tempfan_gpu entry
  cli.py              # CLI parsing, signal handling, main loop
  curve.py            # CSV parsing, validation, numpy interpolation
  gpu.py              # nvidia-smi temperature query
  pwm.py              # sysfs PWM operations + device locking
  plot.py             # matplotlib plotting (optional)
  presets/            # Built-in CSV presets
    quiet.csv
    balanced.csv
    performance.csv
tests/                # pytest tests
```

## License

MIT
