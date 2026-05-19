# tempfan-gpu

一个基于 GPU 温度动态控制 NVIDIA 显卡风扇 PWM 的 Linux 命令行工具。

## 功能

- **温度控制风扇** — 监控 GPU 温度并自动调节风扇转速
- **自定义风扇曲线** — 通过 CSV 文件定义自己的温度-PWM 曲线
- **内置预设** — 选择静音、平衡或性能优先预设
- **多 GPU 支持** — 控制所有检测到的 NVIDIA GPU 中温度最高的那个
- **可视化曲线** — 将风扇曲线绘制为 PNG 图片（可选依赖 matplotlib）
- **安全退出** — 收到 SIGINT/SIGTERM 时自动恢复自动风扇控制
- **设备锁定** — 防止多个实例同时控制同一 PWM 设备

## 安装

```bash
git clone https://github.com/Heliopause0916/tempfan-gpu.git
cd tempfan-gpu
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
# 可选：安装绘图支持
pip install -e ".[plot]"
```

## 使用

### 运行模式

```bash
# 默认曲线：从 0°C 到 100°C 线性 0-255
sudo tempfan-gpu --pwm-device /sys/class/hwmon/hwmon1/pwm1

# 自定义 CSV 曲线
sudo tempfan-gpu --pwm-device /sys/class/hwmon/hwmon1/pwm1 --csv my-curve.csv

# 内置预设
sudo tempfan-gpu --pwm-device /sys/class/hwmon/hwmon1/pwm1 --csv-preset balanced

# 自定义轮询间隔
sudo tempfan-gpu --pwm-device /sys/class/hwmon/hwmon1/pwm1 --interval 10
```

### 绘图模式（无需 root / --pwm-device）

```bash
# 绘制自定义 CSV 曲线
tempfan-gpu plot --csv my-curve.csv --output curve.png

# 自定义温度范围绘图
tempfan-gpu plot --csv my-curve.csv --temp-min 0 --temp-max 90 --output curve.png

# 绘制内置预设曲线
tempfan-gpu plot --csv-preset balanced --output curve.png

# 列出可用预设
tempfan-gpu --csv-preset invalid
```

## 查找 PWM 设备

```bash
ls /sys/class/hwmon/
ls /sys/class/hwmon/hwmon*/pwm*
cat /sys/class/hwmon/hwmon*/name
```

## systemd 服务

创建 `/etc/systemd/system/tempfan-gpu.service`：

```ini
[Unit]
Description=GPU 温度风扇控制器
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

对于多风扇配置，请为不同的 `--pwm-device` 路径创建单独的服务文件。

## 风扇曲线 CSV 格式

```csv
temperature_C,PWM
30,50
50,100
70,180
85,255
```

规则：
- **编码**：utf-8-sig（兼容 BOM）
- **列**：温度（°C）、PWM（0-255）
- **最少**：至少 2 个数据点
- **顺序**：温度和 PWM 都必须非递减（允许相等）
- **PWM 范围**：[0, 255]
- **插值**：通过 `numpy.interp` 线性插值，结果 `round()` 取整
- **钳位**：低于第一个点 → 第一个点 PWM；高于最后一个点 → 最后一个点 PWM

> 注意：`numpy.interp(50.0, [0.0, 100.0], [0, 255])` → `127.5` → `round()` → `127`（不是 128）

## 内置预设

| 预设        | 描述           | 起始温度 (PWM=0) | 满速温度 (PWM=255) | 50°C 时 PWM | 曲线特点               |
|-------------|----------------|------------------|--------------------|-------------|------------------------|
| quiet       | 静音优先       | 30°C             | 85°C               | 64          | 升温慢、风噪低         |
| balanced    | 中庸平衡       | 30°C             | 85°C               | 64          | 散热与噪音平衡         |
| performance | 性能优先       | 20°C             | 70°C               | 102         | 风扇提前介入，散热激进 |

## 参数说明

### 运行模式（`tempfan-gpu`）

| 参数            | 描述                              | 是否必需               |
|-----------------|-----------------------------------|------------------------|
| `--pwm-device`  | PWM 设备路径                      | 是                     |
| `--csv`         | 自定义风扇曲线 CSV 文件           | 否（与 --csv-preset 互斥） |
| `--csv-preset`  | 内置预设（quiet/balanced/performance）| 否（与 --csv 互斥）  |
| `--interval`    | 轮询间隔秒数（默认：5）           | 否                     |

未指定 `--csv` / `--csv-preset` 时使用默认曲线：从 0°C 到 100°C 线性 0-255。

### 绘图子命令（`tempfan-gpu plot`）

| 参数            | 描述                              | 是否必需               |
|-----------------|-----------------------------------|------------------------|
| `--csv`         | 自定义风扇曲线 CSV 文件           | 否（与 --csv-preset 互斥） |
| `--csv-preset`  | 内置预设（quiet/balanced/performance）| 否（与 --csv 互斥） |
| `--output`      | 输出 PNG 文件路径                 | 是                     |
| `--temp-min`    | X 轴最低温度（默认：0）           | 否                     |
| `--temp-max`    | X 轴最高温度（默认：120）         | 否                     |

## NaN/Inf 温度保护

工具优雅处理传感器异常：

- **`gpu.py`**：从 `nvidia-smi` 解析的温度值通过 `math.isfinite()` 过滤，拒绝 NaN、Inf 和 -Inf。
- **`cli.py`**：主循环进行二次 `math.isfinite()` 检查作为纵深防御。
- **`curve.py`**：CSV 温度值在解析时通过 `np.isfinite()` 验证。
- 遇到无效温度读数时，控制器记录告警日志并跳过该轮循环，不会崩溃。

## 设备锁定

使用 `fcntl.flock` 在 `/tmp/tempfan-{device}.lock` 创建设备锁，
防止多个实例同时控制同一 PWM 设备。锁在进程退出时自动释放。
Windows 上为空操作（不创建锁文件）。

## 系统要求

- **操作系统**：仅限 Linux
- **GPU**：具有 `nvidia-smi` 的 NVIDIA GPU
- **权限**：root（用于 sysfs 写入）
- **Python**：>= 3.8

**依赖**：numpy、loguru（必需）；matplotlib（可选，用于 `plot` 子命令）

## 开发

```bash
source .venv/bin/activate
pip install -e ".[plot]"
python -m pytest tests/ -v
```

### 测试说明

- 测试使用 `tempfile.NamedTemporaryFile` 创建临时 CSV 文件，通过 `os.unlink` 清理。
- `test_plot` 默认跳过；设置 `TEMPFAN_TEST_PLOT=1` 启用（需要 matplotlib）。
- 无需外部服务或网络访问。
- `test_gpu` 验证类型契约；无 NVIDIA GPU 时返回 `None`。

## 项目结构

```
src/tempfan_gpu/
  __main__.py         # python -m tempfan_gpu 入口
  cli.py              # CLI 解析、信号处理、主循环
  curve.py            # CSV 解析、校验、numpy 插值
  gpu.py              # nvidia-smi 温度查询
  pwm.py              # sysfs PWM 操作 + 设备锁定
  plot.py             # matplotlib 绘图（可选，plot 子命令）
  presets/            # 内置 CSV 预设
    quiet.csv
    balanced.csv
    performance.csv
tests/                # pytest 测试
  test_curve.py
  test_gpu.py
  test_pwm.py
  test_pwm_lock.py
  test_presets.py
  test_plot.py        # 默认跳过
```

## 退出安全

收到 SIGINT/SIGTERM 或正常退出时，工具自动向 `pwmX_enable` 写入 `0`，
恢复自动风扇控制。通过以下三层机制保证：

1. **信号处理器**：`signal.signal()` 捕获 SIGINT/SIGTERM。
2. **`try/finally`**：主循环的 `finally` 块执行 `set_pwm_auto_mode()`。
3. **`atexit`**：锁文件在进程退出时自动释放。

如果工具意外退出，风扇硬件不会停留在手动模式。

## 许可证

MIT
