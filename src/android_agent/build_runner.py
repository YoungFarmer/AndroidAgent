from __future__ import annotations

from pathlib import Path

from android_agent.config import ProjectConfig
from android_agent.models import BuildResult, Status
from android_agent.shell import CommandRunner, persist_command_result


def _split_command(command: str) -> list[str]:
    return command.split()


def _find_latest_apk(project_path: Path, pattern: str) -> Path | None:
    candidates = sorted(project_path.glob(pattern), key=lambda item: item.stat().st_mtime, reverse=True)
    return candidates[0] if candidates else None


def run_build(config: ProjectConfig, runner: CommandRunner, run_dir: Path) -> BuildResult:
    build_log = run_dir / "build.log"
    command = _split_command(config.gradle_command) + [config.assemble_task]
    result = runner.run(command, cwd=config.project_path, timeout=1800)
    persist_command_result(build_log, result)

    test_apk_path: Path | None = None
    if result.ok and config.instrumentation.enabled:
        install_test_result = runner.run(_split_command(config.gradle_command) + [config.instrumentation.install_task], cwd=config.project_path, timeout=1800)
        build_log.write_text(build_log.read_text(encoding="utf-8") + "\n\n# instrumentation\n\n", encoding="utf-8")
        with build_log.open("a", encoding="utf-8") as handle:
            handle.write(f"$ {' '.join(install_test_result.command)}\n")
            handle.write(install_test_result.merged_output() + "\n")
        if install_test_result.ok:
            test_apk_path = _find_latest_apk(config.project_path, "**/*androidTest*.apk")

    apk_path = _find_latest_apk(config.project_path, "**/outputs/apk/**/*.apk")
    failure_reason = None
    status = Status.PASS
    if not result.ok:
        status = Status.FAIL
        failure_reason = "gradle build failed"
    elif apk_path is None:
        status = Status.FAIL
        failure_reason = "debug apk not found after build"

    return BuildResult(
        status=status,
        task=config.assemble_task,
        apk_path=str(apk_path) if apk_path else None,
        android_test_apk_path=str(test_apk_path) if test_apk_path else None,
        log_path=str(build_log),
        command_result=result,
        failure_reason=failure_reason,
    )
