# AndroidAgent

一个独立运行的 Android 自动化 Agent CLI，命令前缀为 `aagent`。

当前仓库已实现第一阶段原型能力：

- `aagent doctor`：检查 Java / ADB / Android SDK / Maestro / 设备 / 应用配置
- `aagent build`：构建、安装并启动目标 App
- `aagent run --case <case_id>`：执行基于 YAML DSL 的 Maestro 流程
- `aagent report --run-id <id>`：定位运行报告和摘要文件

当前阶段对应路线图进度：

- 里程碑一：基础环境探测，已实现
- 里程碑二：构建与安装链路，已实现
- 里程碑三及之后：待继续推进

## 安装

推荐使用仓库内虚拟环境，尤其是在离线环境或不希望写入全局 Python 目录时。
在 Homebrew Python 3.12+ / 3.14 环境下，新建 venv 默认通常只有 `pip`，不再自带 `setuptools`。如果直接对依赖 `setuptools.build_meta` 的项目执行 `--no-build-isolation`，常见报错会是 `Cannot import 'setuptools.build_meta'`。当前仓库已经改成自带构建后端，默认安装不需要预装 `setuptools`。
另外，不建议使用 `--system-site-packages`，否则可能重新落回系统包管理并触发 `externally-managed-environment`。

```bash
cd /path/to/AndroidAgent
python3 -m venv .venv
. .venv/bin/activate
python3 -m pip install -e .
```

安装完成后，验证 CLI：

```bash
aagent --help
```

如果你本机的 `python3 -m pip install -e .` 报了 `SSLCertVerificationError`，可以临时指定 `certifi` 的 CA 证书：

```bash
SSL_CERT_FILE=$(python3 -c 'import certifi; print(certifi.where())') python3 -m pip install -e .
```

如果你明确需要关闭构建隔离，可以继续使用：

```bash
python3 -m pip install -e . --no-build-isolation
```

这一步现在不再要求 venv 里预装 `setuptools`，但运行时依赖 `PyYAML` 仍然需要能从包源安装，或者提前在环境中准备好。

如果你不想激活虚拟环境，也可以直接使用：

```bash
.venv/bin/aagent --help
```

## 配置

示例配置位于 [configs/agent.example.yaml]。

核心字段包括：

- `project_path`：外部 Android 项目路径，推荐使用相对路径或环境变量
- `gradle_command`：Gradle wrapper 或命令
- `assemble_task`：默认构建任务，当前为 `assembleDebug`
- `build_retries`：构建失败后的重试次数
- `device_serial`：默认设备序列号
- `uninstall_before_install`：安装前是否卸载旧包
- `install_retries`：安装失败后的重试次数
- `launch_retries`：启动失败后的重试次数
- `app.package_name`：目标包名
- `app.test_package_name`：Instrumentation 测试包名，开启测试包安装时用于卸载旧测试包
- `app.launch_activity` 或 `app.deep_link`：默认启动方式
- `maestro_cases_dir`：测试用例目录
- `instrumentation.enabled`：开启后会在构建成功后执行 `installDebugAndroidTest`
- `instrumentation.install_task`：Instrumentation 测试安装任务，默认 `installDebugAndroidTest`

路径建议：

- 仓库内目录尽量写成相对 `configs/*.yaml` 的路径，例如 `./cases`、`../outputs`
- 外部 Android 项目如果在不同机器位置不一致，建议使用环境变量，例如 `project_path: ${ANDROID_PROJECT_PATH}`
- 配置加载时会自动展开 `~` 和环境变量，并把相对路径解释为“相对于配置文件所在目录”

## 示例命令

```bash
aagent doctor --config configs/agent.example.yaml
aagent build --config configs/agent.example.yaml
aagent run --config configs/agent.example.yaml --case login_dialog_check
aagent report --config configs/agent.example.yaml --run-id run-20260322T000000Z
```

## 阶段一里程碑验证

### 里程碑一：基础环境探测

目标是确认执行链路的前置条件已经具备，包括 Java、ADB、Android SDK、设备连接和 App 启动配置。

推荐按下面顺序验证：

```bash
.venv/bin/aagent doctor --config configs/agent.example.yaml
```

如果你没有激活虚拟环境，也可以先执行：

```bash
. .venv/bin/activate
aagent doctor --config configs/agent.example.yaml
```

验证通过时，你应该能看到：

- 终端输出 `aagent doctor completed with status=PASS` 或 `WARN`
- 终端打印 JSON 报告和 Markdown 报告路径
- 报告中能看到至少一台已连接设备的序列号、Android 版本和分辨率
- 报告中能明确看到哪些检查项通过，哪些检查项失败

报告位置：

- `outputs/reports/doctor-*.json`
- `outputs/reports/doctor-*.md`

如果验证失败，优先检查：

- `adb devices -l` 是否能看到目标设备
- 配置中的 `device_serial` 是否和真机序列号一致
- `ANDROID_HOME` / `ANDROID_SDK_ROOT` 是否已配置
- `app.package_name` 和 `app.launch_activity` 是否填写正确

### 里程碑二：构建与安装链路

目标是稳定完成 `assembleDebug -> install/reinstall -> launch`，并在开启 instrumentation 时补执行 `installDebugAndroidTest`。

#### 1. 先验证 build 命令

```bash
.venv/bin/aagent build --config configs/agent.example.yaml
aagent run --config configs/sunflower.yaml --case sunflower_launch_check
```

这个命令会执行：

- Gradle `assembleDebug`
- 失败时按 `build_retries` 重试
- 如果 `uninstall_before_install: true`，先卸载旧包
- `adb install -r <apk>`
- 失败时按 `install_retries` 重试
- 按 `app.deep_link`、`app.launch_activity` 或 Launcher 方式启动 App
- 启动失败时按 `launch_retries` 重试

验证通过时，你应该能看到：

- 终端输出 `run_id=...`
- 终端输出 `status=PASS`
- 终端打印 `report=` 和 `summary=` 路径

本次运行的关键产物位于：

- `outputs/runs/<run_id>/build.log`
- `outputs/runs/<run_id>/install.log`
- `outputs/runs/<run_id>/launch.log`
- `outputs/runs/<run_id>/logcat.txt`
- `outputs/runs/<run_id>/summary.json`
- `outputs/runs/<run_id>/report.md`

重点查看点：

- `build.log` 中是否记录了 `assembleDebug`，以及重试日志
- `install.log` 中是否记录了卸载旧包和安装结果
- `launch.log` 中是否记录了启动命令和重试结果
- `summary.json` 中的 `build_result`、`install_result`、`failure_reason` 是否完整

#### 2. 验证 instrumentation 安装链路

先把配置改成：

```yaml
instrumentation:
  enabled: true
  install_task: installDebugAndroidTest
```

同时确认：

```yaml
app:
  package_name: com.example.app
  test_package_name: com.example.app.test
```

然后再次执行：

```bash
.venv/bin/aagent build --config configs/agent.example.yaml
```

验证通过时，你应该能在 `build.log` 里看到 `installDebugAndroidTest`，并且安装前会尝试卸载旧的测试包。

#### 3. 验证 deep link 启动

如果你想验证 case 级 deep link 覆盖默认启动方式，可以新增或修改一个 case，例如：

```yaml
name: deep_link_open
app_id: com.example.app
deep_link: myapp://details/42
steps:
  - action: launch
  - action: assert_visible
    target: 详情页
```

然后执行：

```bash
.venv/bin/aagent run --config configs/agent.example.yaml --case deep_link_open
```

验证通过时，`launch.log` 中应出现类似下面的启动命令：

```bash
adb -s <serial> shell am start -W -a android.intent.action.VIEW -d myapp://details/42
```

如果没有提供 case 级 `deep_link`，系统会回退到配置里的 `app.deep_link` 或 `app.launch_activity`。

#### 4. 推荐做一次稳定性回归

里程碑二的验收不是只跑通一次，建议至少连续执行 3 次：

```bash
.venv/bin/aagent build --config configs/agent.example.yaml
.venv/bin/aagent build --config configs/agent.example.yaml
.venv/bin/aagent build --config configs/agent.example.yaml
```

重点确认：

- 旧包卸载和重装没有偶发卡住
- 重试后失败原因会写进日志，而不是静默失败
- 每次都会生成新的 `run_id` 和对应报告

如果失败，常见定位方法：

- 安装失败：先看 `install.log`，重点关注 `INSTALL_FAILED_*`
- 启动失败：看 `launch.log`，确认 Activity 或 deep link 是否正确
- 构建失败：看 `build.log`，确认 Gradle 任务名和模块是否匹配你的 Android 项目

## 当前限制

当前 `aagent build` 会完成“构建 + 安装 + 启动”，但还不会单独安装 instrumentation APK 到设备；当前实现是按路线图要求在构建阶段执行 `installDebugAndroidTest` 任务并把结果写入 `build.log`。如果你的 Android 项目里这个任务本身已经包含设备安装，那么它会直接生效；如果你的项目只产出测试 APK 文件，后续可以继续补独立安装步骤。

## 目录结构

```text
configs/
  agent.example.yaml
  cases/
src/android_agent/
templates/
tests/
outputs/
```

## 测试

```bash
.venv/bin/python -m pytest -q
```

如果你当前 shell 里直接运行 `pytest` 仍提示 `No module named 'yaml'` 或其他依赖缺失，优先使用虚拟环境里的解释器：

```bash
.venv/bin/python -m pytest tests/test_build_runner.py tests/test_device_manager.py tests/test_config.py tests/test_cli.py tests/test_doctor.py tests/test_maestro_executor.py tests/test_reporter.py
```
