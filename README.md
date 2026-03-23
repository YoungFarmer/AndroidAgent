# AndroidAgent

一个独立运行的 Android 自动化 Agent CLI，命令前缀为 `aagent`。

当前仓库已实现第一阶段原型能力：

- `aagent doctor`：检查 Java / ADB / Android SDK / Maestro / 设备 / 应用配置
- `aagent build`：构建、安装并启动目标 App
- `aagent run --case <case_id>`：执行基于 YAML DSL 的 Maestro 流程
- `aagent report --run-id <id>`：定位运行报告和摘要文件

## 安装

推荐使用仓库内虚拟环境，尤其是在离线环境或不希望写入全局 Python 目录时。
在 Homebrew Python 环境下，不建议使用 `--system-site-packages`，否则可能重新落回系统包管理并触发 `externally-managed-environment`。

```bash
cd /path/to/AndroidAgent
python3 -m venv .venv
. .venv/bin/activate
python3 -m pip install -e . --no-build-isolation
```

安装完成后，验证 CLI：

```bash
aagent --help
```

如果你本机的 `python3 -m pip install -e .` 报了 `SSLCertVerificationError` 或 `Could not find a version that satisfies the requirement setuptools`，可以临时指定 `certifi` 的 CA 证书：

```bash
SSL_CERT_FILE=$(python3 -c 'import certifi; print(certifi.where())') python3 -m pip install -e .
```

如果你不想激活虚拟环境，也可以直接使用：

```bash
.venv/bin/aagent --help
```

## 配置

示例配置位于 [configs/agent.example.yaml]。

核心字段包括：

- `project_path`：外部 Android 项目路径，推荐使用相对路径或环境变量
- `gradle_command`：Gradle wrapper 或命令
- `device_serial`：默认设备序列号
- `app.package_name`：目标包名
- `app.launch_activity` 或 `app.deep_link`：启动方式
- `maestro_cases_dir`：测试用例目录

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
