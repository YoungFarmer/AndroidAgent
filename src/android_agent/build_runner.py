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


def _find_latest_main_apk(project_path: Path) -> Path | None:
    candidates = sorted(
        (item for item in project_path.glob("**/outputs/apk/**/*.apk") if "androidTest" not in item.name),
        key=lambda item: item.stat().st_mtime,
        reverse=True,
    )
    return candidates[0] if candidates else None


def _append_command_result(path: Path, result, *, title: str | None = None) -> None:
    with path.open("a", encoding="utf-8") as handle:
        if title:
            handle.write(f"\n\n# {title}\n\n")
        handle.write(f"$ {' '.join(result.command)}\n")
        merged_output = result.merged_output()
        if merged_output:
            handle.write(merged_output)
            handle.write("\n")
        handle.write(f"exit_code={result.returncode}\n")
        handle.write(f"duration_seconds={result.duration_seconds}\n")


def run_build(config: ProjectConfig, runner: CommandRunner, run_dir: Path) -> BuildResult:
    build_log = run_dir / "build.log"
    command = _split_command(config.gradle_command) + [config.assemble_task]
    attempts = max(config.build_retries, 1)
    result = runner.run(command, cwd=config.project_path, timeout=1800)
    persist_command_result(build_log, result)
    for attempt in range(2, attempts + 1):
        if result.ok:
            break
        retried = runner.run(command, cwd=config.project_path, timeout=1800)
        _append_command_result(build_log, retried, title=f"assemble retry {attempt}")
        result = retried

    test_apk_path: Path | None = None
    instrumentation_result = None
    if result.ok and config.instrumentation.enabled:
        instrumentation_result = runner.run(
            _split_command(config.gradle_command) + [config.instrumentation.install_task],
            cwd=config.project_path,
            timeout=1800,
        )
        _append_command_result(build_log, instrumentation_result, title="instrumentation")
        if instrumentation_result.ok:
            test_apk_path = _find_latest_apk(config.project_path, "**/*androidTest*.apk")

    apk_path = _find_latest_main_apk(config.project_path)
    failure_reason = None
    status = Status.PASS
    if not result.ok:
        status = Status.FAIL
        failure_reason = f"gradle build failed: {result.merged_output() or 'no output'}"
    elif instrumentation_result is not None and not instrumentation_result.ok:
        status = Status.FAIL
        failure_reason = f"instrumentation install task failed: {instrumentation_result.merged_output() or 'no output'}"
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
