# AndroidAgent 使用文档：Sunflower 项目

本文档说明如何在当前机器上安装并使用 `aagent`，并以 `sunflower` 作为测试项目。

## 1. 当前已确认的信息

- AndroidAgent 仓库路径：当前仓库根目录
- Sunflower 项目路径：默认相对 `configs/sunflower.yaml` 解析到 `../../sunflower`
- Gradle 入口：`../../sunflower/gradlew`
- App 包名：`com.google.samples.apps.sunflower`
- Launcher Activity：`.GardenActivity`
- Android SDK 本地路径：本机 `ANDROID_HOME` 或 `ANDROID_SDK_ROOT` 对应目录
- 设备查询结果：截至 `2026-03-22` 本次检查时，`adb devices -l` 没有返回任何已连接设备

这些信息分别来自：

- `app/build.gradle`
- `app/src/main/AndroidManifest.xml`
- `local.properties`

## 2. 安装方式

### 2.1 安装前提

确保你的机器上已经可用：

- `python3`
- `pip`
- `java`
- `adb`
- `maestro`

如果要手工确认，可以运行：

```bash
python3 --version
java -version
adb version
maestro --version
```

### 2.2 安装 AndroidAgent

推荐使用仓库内虚拟环境，不依赖用户目录安装，也更适合当前这种离线环境。

进入仓库根目录：

```bash
cd /path/to/AndroidAgent
```

执行：

```bash
python3 -m venv .venv
. .venv/bin/activate
python3 -m pip install -e .
```

安装完成后，验证 CLI 是否可用：

```bash
aagent --help
```

如果你不想激活虚拟环境，也可以直接执行：

```bash
.venv/bin/aagent --help
```

## 3. Sunflower 项目准备

### 3.1 配置文件

仓库里已经准备好了 Sunflower 专用配置：

- `configs/sunflower.yaml`

这个配置已经写好了：

- `project_path=../../sunflower`
- `package_name=com.google.samples.apps.sunflower`
- `launch_activity=.GardenActivity`
- `maestro_cases_dir=./cases`
- `output.base_dir=../outputs`

你通常只需要补一个字段：

- `device_serial`

如果你的 Sunflower 不在这个相对位置，再改成你自己的相对路径，或者改成环境变量写法，例如 `project_path: ${ANDROID_PROJECT_PATH}`。

### 3.2 Sunflower 的额外说明

Sunflower 的 README 说明了一个额外前置条件：

- 如果要完整使用图库相关功能，需要配置 `unsplash_access_key`

配置方式是在 `~/.gradle/gradle.properties` 或项目根目录的 `gradle.properties` 中增加：

```properties
unsplash_access_key=<your Unsplash access key>
```

不过即使没有这个 key，App 仍然可以启动，只是图库页面不可用。所以如果你当前只是验证 `doctor`、`build`、`launch` 和基础首页流程，可以先不配置。

## 4. 设备序列号怎么获取

### 4.1 最常用命令

连接真机或启动模拟器后，运行：

```bash
adb devices -l
```

你会看到类似输出：

```text
List of devices attached
emulator-5554          device product:sdk_gphone64_arm64 model:sdk_gphone64_arm64 device:emu64a transport_id:1
R5CX123ABC             device usb:339738624X product:xxx model:Galaxy_S23 device:dm1q transport_id:2
```

其中第一列就是设备序列号：

- 模拟器示例：`emulator-5554`
- 真机示例：`R5CX123ABC`

### 4.2 当前这台机器的实际情况

我刚刚实际执行过：

```bash
adb devices -l
```

结果是空列表，也就是当前没有已连接设备。  
所以现在还不能把真实序列号写进配置里。

### 4.3 连接后怎么填进配置

拿到序列号后，编辑：

- `configs/sunflower.yaml`

把这一行：

```yaml
device_serial:
```

改成例如：

```yaml
device_serial: emulator-5554
```

或者：

```yaml
device_serial: R5CX123ABC
```

## 5. 如何使用 aagent

下面所有命令都建议在这个目录执行：

```bash
cd /path/to/AndroidAgent
. .venv/bin/activate
```

### 5.1 环境检查

```bash
aagent doctor --config configs/sunflower.yaml
```

作用：

- 检查 `java`
- 检查 `adb`
- 检查 `maestro`
- 检查 Android SDK 环境变量
- 检查设备连接
- 检查 App 包名和启动配置

输出：

- 终端摘要
- `outputs/reports/doctor-<timestamp>.json`
- `outputs/reports/doctor-<timestamp>.md`

如果没有设备，或者 `device_serial` 配了但设备未连接，`doctor` 会明确报出来。

### 5.2 构建、安装和启动

```bash
aagent build --config configs/sunflower.yaml
```

作用：

- 在 Sunflower 项目根目录执行 `./gradlew assembleDebug`
- 找到构建产物 APK
- 通过 ADB 安装 APK
- 启动 `com.google.samples.apps.sunflower/.GardenActivity`
- 收集构建和启动日志

输出目录：

```text
outputs/runs/<run_id>/
  build.log
  install.log
  launch.log
  logcat.txt
  timeline.json
  summary.json
  report.md
```

### 5.3 执行测试流程

仓库中已经有一个适用于 Sunflower 首页的示例 case：

- `configs/cases/sunflower_launch_check.yaml`

运行命令：

```bash
aagent run --config configs/sunflower.yaml --case sunflower_launch_check
```

这个 case 当前做的事情是：

1. 启动 Sunflower
2. 断言首页存在 `My garden`
3. 断言首页存在 `Add plant`

这两个文案来自 Sunflower 的字符串资源，稳定性相对更好，适合当第一条冒烟用例。

### 5.4 查看报告路径

如果你已经知道某次运行的 `run_id`，可以执行：

```bash
aagent report --config configs/sunflower.yaml --run-id <run_id>
```

它会直接打印：

- `report.md` 路径
- `summary.json` 路径

## 6. 一条推荐的实际操作流程

第一次使用建议按下面顺序来：

1. 连接模拟器或真机。
2. 运行 `adb devices -l`，确认序列号。
3. 把序列号填进 `configs/sunflower.yaml`。
4. 运行 `aagent doctor --config configs/sunflower.yaml`。
5. 如果 `doctor` 通过，再运行 `aagent build --config configs/sunflower.yaml`。
6. 构建安装成功后，运行 `aagent run --config configs/sunflower.yaml --case sunflower_launch_check`。
7. 去 `outputs/runs/<run_id>/report.md` 查看执行结果。

## 7. 常见问题

### 7.1 `aagent: command not found`

原因：

- 没有激活 `.venv`
- 没有执行 `python3 -m pip install -e .`

解决方式：

```bash
cd /path/to/AndroidAgent
python3 -m venv .venv
. .venv/bin/activate
python3 -m pip install -e .
```

如果你想立刻验证，也可以先这样运行：

```bash
.venv/bin/aagent doctor --config configs/sunflower.yaml
```

### 7.2 `pip install -e .` 出现 `subprocess-exited-with-error`

这次你遇到的就是这个问题，根因通常是两个叠加：

- `pip` 默认会为 `pyproject.toml` 项目创建隔离构建环境
- 关闭构建隔离后，构建后端本身必须已经能在当前环境导入
- Python 3.12+ / 3.14 新建 venv 默认往往只有 `pip`，不再自带 `setuptools`

当前仓库已经内置了构建后端，因此默认安装方式直接使用：

```bash
cd /path/to/AndroidAgent
python3 -m venv .venv
. .venv/bin/activate
python3 -m pip install -e .
```

如果你仍然想显式加上 `--no-build-isolation`，现在也可以继续这样执行：

```bash
python3 -m pip install -e . --no-build-isolation
```

如果错误里带有 `SSLCertVerificationError`、`certificate verify failed`，可以直接把 `certifi` 的 CA 证书传给 `pip`：

```bash
SSL_CERT_FILE=$(python3 -c 'import certifi; print(certifi.where())') python3 -m pip install -e .
```

如果随后报的是 `Could not find a version that satisfies the requirement PyYAML`，那说明问题已经从“构建后端缺失”变成了“运行时依赖无法下载”，需要检查网络、证书或内部镜像源。

### 7.3 `doctor` 里设备检测失败

先检查：

```bash
adb devices -l
```

如果输出为空：

- 模拟器没启动
- 真机没授权 USB 调试
- ADB 服务异常

可以尝试：

```bash
adb kill-server
adb start-server
adb devices -l
```

### 7.4 Sunflower 能启动但某些页面失败

这是预期内可能发生的，因为：

- 当前第一阶段执行器以 `Maestro` 为主
- 示例 case 还是通用型 DSL
- 真实业务流程往往需要按实际 UI 文案和控件继续定制

建议先从 `sunflower_launch_check` 这种首页冒烟用例开始，再逐步补更具体的 case。

## 8. 相关文件

- 安装和通用说明：`README.md`
- Sunflower 配置：`configs/sunflower.yaml`
- Sunflower 冒烟 case：`configs/cases/sunflower_launch_check.yaml`
- 示例配置：`configs/agent.example.yaml`
