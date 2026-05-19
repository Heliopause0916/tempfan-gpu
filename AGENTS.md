# AGENTS.md - tempfan-gpu

一个基于 GPU 温度动态控制 NVIDIA 显卡风扇 PWM 的 Linux 命令行工具。

## 项目结构

```
src/tempfan_gpu/          # 源码 (src/ layout, pyproject.toml)
  __main__.py             # python -m tempfan_gpu 入口
  cli.py                  # CLI 解析、信号处理、主循环 (entry_point)
  curve.py                # CSV 曲线解析、默认曲线、numpy 插值
  gpu.py                  # 调用 nvidia-smi 查询温度
  pwm.py                  # 读写 sysfs PWM 设备文件 + fcntl 锁机制
  plot.py                 # matplotlib 绘图 (可选依赖)
  presets/                # 内置 CSV 预设模板
    quiet.csv             #   静音优先
    balanced.csv          #   平衡曲线
    performance.csv       #   性能优先
tests/                    # pytest 测试
  test_curve.py           #   curve 模块测试
  test_gpu.py             #   gpu 模块测试
  test_pwm.py             #   pwm 模块测试
  test_pwm_lock.py        #   pwm 锁机制测试
  test_presets.py         #   内置预设测试
  test_plot.py            #   绘图测试 (默认跳过, 需 TEMPFAN_TEST_PLOT=1)
```

## 关键命令

```bash
# 激活虚拟环境 (Windows)
.venv\Scripts\Activate.ps1

# 激活虚拟环境 (Linux/macOS)
source .venv/bin/activate

# 安装 (dev, 必需在 .venv 激活后执行)
pip install -e .

# 安装含 plot 支持
pip install -e ".[plot]"

# 无需激活也可直接调用 .venv 内的 python
.venv/Scripts/python -m pytest tests/ -v
.venv/Scripts/tempfan-gpu --help

# 运行所有测试
python -m pytest tests/ -v

# 运行单个测试模块
python -m pytest tests/test_curve.py -v
python -m pytest tests/test_presets.py -v

# 运行 (需 Linux + NVIDIA GPU)
tempfan-gpu --pwm-device /sys/class/hwmon/hwmon1/pwm1

# 使用自定义曲线
tempfan-gpu --pwm-device /sys/class/hwmon/hwmon1/pwm1 --csv my-curve.csv

# 使用内置预设曲线 (--csv 与 --csv-preset 互斥)
tempfan-gpu --pwm-device /sys/class/hwmon/hwmon1/pwm1 --csv-preset balanced

# 自定义轮询间隔
tempfan-gpu --pwm-device /sys/class/hwmon/hwmon1/pwm1 --interval 10

# 绘制 CSV 曲线图 (需安装 matplotlib, 不需要 --pwm-device)
tempfan-gpu --plot my-curve.csv --output curve.png
```

## 必须避免的陷阱

### 必须使用 .venv 虚拟环境
- 禁止使用系统级 Python 安装依赖或运行工具
- 所有操作 (安装、测试、运行) 都必须在 .venv 激活的状态下执行
- .venv/ 已在 .gitignore 中, 不会提交到版本库

### --pwm-device 是运行模式必填参数
- 没有环境变量回退 (PWM_DEVICE 已被移除)
- 运行模式下必须显式传入, 如 --pwm-device /sys/class/hwmon/hwmon1/pwm1
- plot 模式 (--plot) 不需要 --pwm-device

### 退出安全 -- 必须恢复自动风扇控制
- cli.py 通过 SIGINT/SIGTERM 信号处理器 + try/finally 确保退出时写 0 到 pwmX_enable
- 任何修改 pwm.py 或 cli.py 中退出流程的改动, 必须保持这个机制, 否则风扇会失去自动控制

### CSV 曲线规格
- 编码: utf-8-sig (兼容 BOM), 两列: 温度(C), PWM(0-255)
- 温度和 PWM 都必须非递减 (允许相等)
- PWM 值必须在 [0, 255] 范围内
- 至少 2 个数据点
- 不再要求首点 PWM=0 或末点 PWM=255, 完全由用户定义
- 插值使用 numpy.interp, 结果 round() 取整
- 注意: numpy.interp(50.0, [0.0, 100.0], [0, 255]) -> round(127.5) -> 127 (不是 128)

### 内置预设曲线 (--csv-preset)
- 三个预设: quiet (静音优先), balanced (平衡), performance (性能优先)
- --csv 与 --csv-preset 是互斥参数, 不能同时使用
- 预设文件位于 src/tempfan_gpu/presets/*.csv, 通过 package-data 打包

### 锁文件 (Linux 专用)
- pwm.py 使用 fcntl.flock 在 /tmp/tempfan-{device_name}.lock 创建设备锁
- 防止同一 PWM 设备被多个 tempfan-gpu 实例同时控制
- 锁在进程退出时自动释放 (atexit 注册清理函数)
- Windows 上是空操作 (no-op), fcntl 在函数内动态导入
- 如果一个实例持有锁, 第二个实例启动时会报错退出

### Plot 子命令 (--plot)
- 需要安装 pip install tempfan-gpu[plot] (或 pip install -e ".[plot]")
- 不需要 --pwm-device, 纯离线绘图
- --output 是 --plot 模式下的必填参数
- 输出 PNG 图片, dpi=150, 双纵轴 (百分比 + PWM 值)
- 纵轴范围根据实际数据的最大 PWM 值动态调整

### Linux 专用
- 依赖 /sys/class/hwmon/... sysfs 接口 (Windows/macOS 不可用)
- 依赖 nvidia-smi 查询温度 (无 NVIDIA GPU 时返回空列表)
- PWM 写操作需要 root 权限

### 测试注意事项
- tests/test_gpu.py 需要 nvidia-smi 可用才能返回非 None 数据; 无 GPU 环境仅验证类型契约
- tests/test_pwm.py 中 test_resolve_pwm_device_empty 需要抑制 loguru 输出 (logger.remove())
- tests/test_plot.py 默认跳过, 设置 TEMPFAN_TEST_PLOT=1 且安装 matplotlib 后才执行
- tests/test_pwm_lock.py 在 Windows 上验证 no-op, 在 Linux 上验证不抛出意外异常
- 所有测试文件使用 tempfile.NamedTemporaryFile 创建临时 CSV 文件, 用 os.unlink 清理
- 测试不依赖 conftest、fixture 或外部服务

## 依赖

运行时: numpy (插值/校验)、loguru (日志)
可选: matplotlib (绘图, [plot] extra)
构建: setuptools >= 61.0, build-backend = "setuptools.build_meta"

## 构建与入口

```toml
[project.scripts]
tempfan-gpu = "tempfan_gpu.cli:entry_point"
```

同时也支持 python -m tempfan_gpu (通过 __main__.py 调用同一个 entry_point)。
