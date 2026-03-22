from __future__ import annotations

from pathlib import Path

from android_agent.config import ProjectConfig
from android_agent.models import CommandResult, InstallResult, Status
from android_agent.shell import CommandRunner, persist_command_result


def _adb_prefix(config: ProjectConfig) -> list[str]:
    prefix = [config.execution.adb_bin]
    if config.device_serial:
        prefix.extend(["-s", config.device_serial])
    return prefix


def install_and_launch(
    config: ProjectConfig,
    runner: CommandRunner,
    run_dir: Path,
    apk_path: Path,
) -> InstallResult:
    install_log = run_dir / "install.log"
    launch_log = run_dir / "launch.log"
    commands: list[CommandResult] = []
    failure_reason = None
    status = Status.PASS

    if config.app is None:
        raise ValueError("app config is required for install and launch")

    adb = _adb_prefix(config)
    if config.uninstall_before_install:
        uninstall_result = runner.run([*adb, "uninstall", config.app.package_name], timeout=60)
        commands.append(uninstall_result)

    install_result: CommandResult | None = None
    attempts = max(config.install_retries, 1)
    for _ in range(attempts):
        install_result = runner.run([*adb, "install", "-r", str(apk_path)], timeout=300)
        commands.append(install_result)
        if install_result.ok:
            break
    if install_result is None or not install_result.ok:
        status = Status.FAIL
        failure_reason = "apk install failed"

    merged_install_text = []
    for result in commands:
        merged_install_text.append(f"$ {' '.join(result.command)}")
        merged_install_text.append(result.merged_output())
        merged_install_text.append("")
    install_log.write_text("\n".join(merged_install_text).strip() + "\n", encoding="utf-8")

    launch_result = None
    if status is Status.PASS:
        if config.app.deep_link:
            launch_cmd = [*adb, "shell", "am", "start", "-a", "android.intent.action.VIEW", "-d", config.app.deep_link]
        elif config.app.launch_activity:
            launch_cmd = [*adb, "shell", "am", "start", "-n", f"{config.app.package_name}/{config.app.launch_activity}"]
        else:
            launch_cmd = [*adb, "shell", "monkey", "-p", config.app.package_name, "-c", "android.intent.category.LAUNCHER", "1"]
        launch_result = runner.run(launch_cmd, timeout=120)
        persist_command_result(launch_log, launch_result)
        if not launch_result.ok:
            status = Status.FAIL
            failure_reason = "app launch failed"
    else:
        launch_log.write_text("launch skipped because install failed\n", encoding="utf-8")

    return InstallResult(
        status=status,
        package_name=config.app.package_name,
        serial=config.device_serial or "default",
        install_log_path=str(install_log),
        launch_log_path=str(launch_log),
        install_command_results=commands,
        launch_command_result=launch_result,
        failure_reason=failure_reason,
    )
