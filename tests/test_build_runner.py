from pathlib import Path

from android_agent.build_runner import run_build
from android_agent.config import load_config
from android_agent.models import CommandResult, Status


class FakeBuildRunner:
    def __init__(self, project_path: Path) -> None:
        self.project_path = project_path
        self.commands: list[list[str]] = []
        self.envs: list[dict[str, str] | None] = []
        self.assemble_attempts = 0

    def run(self, command, *, cwd=None, timeout=None, env=None):
        self.commands.append(command)
        self.envs.append(env)
        if command[-1] == "assembleDebug":
            self.assemble_attempts += 1
            if self.assemble_attempts == 1:
                return CommandResult(command, 1, "", "assemble failed", 0.1)
            apk_path = self.project_path / "app" / "build" / "outputs" / "apk" / "debug" / "app-debug.apk"
            apk_path.parent.mkdir(parents=True, exist_ok=True)
            apk_path.write_text("apk", encoding="utf-8")
            return CommandResult(command, 0, "assemble ok", "", 0.2)

        if command[-1] == "installDebugAndroidTest":
            test_apk_path = self.project_path / "app" / "build" / "outputs" / "apk" / "androidTest" / "debug" / "app-debug-androidTest.apk"
            test_apk_path.parent.mkdir(parents=True, exist_ok=True)
            test_apk_path.write_text("test-apk", encoding="utf-8")
            return CommandResult(command, 0, "install test ok", "", 0.1)

        return CommandResult(command, 0, "ok", "", 0.1)


def test_run_build_retries_and_runs_instrumentation_task(tmp_path: Path) -> None:
    project_path = tmp_path / "sample-android-project"
    project_path.mkdir()
    run_dir = tmp_path / "run"
    run_dir.mkdir()

    config = load_config(Path("configs/agent.example.yaml"))
    config.project_path = project_path
    config.instrumentation.enabled = True

    runner = FakeBuildRunner(project_path)
    result = run_build(config, runner, run_dir)

    assert result.status is Status.PASS
    assert result.apk_path is not None
    assert result.android_test_apk_path is not None
    assert runner.commands.count(["./gradlew", "assembleDebug"]) == 2
    assert ["./gradlew", "installDebugAndroidTest"] in runner.commands
    assert all(env is not None and env["GRADLE_USER_HOME"].endswith("outputs/.gradle") for env in runner.envs)
    assert "assemble retry 2" in (run_dir / "build.log").read_text(encoding="utf-8")


def test_run_build_finds_apk_in_intermediates_directory(tmp_path: Path) -> None:
    project_path = tmp_path / "sample-android-project"
    project_path.mkdir()
    run_dir = tmp_path / "run"
    run_dir.mkdir()

    config = load_config(Path("configs/agent.example.yaml"))
    config.project_path = project_path

    class IntermediatesRunner:
        def run(self, command, *, cwd=None, timeout=None, env=None):
            apk_path = project_path / "app" / "build" / "intermediates" / "apk" / "debug" / "app-debug.apk"
            apk_path.parent.mkdir(parents=True, exist_ok=True)
            apk_path.write_text("apk", encoding="utf-8")
            return CommandResult(command, 0, "assemble ok", "", 0.2)

    result = run_build(config, IntermediatesRunner(), run_dir)

    assert result.status is Status.PASS
    assert result.apk_path == str(project_path / "app" / "build" / "intermediates" / "apk" / "debug" / "app-debug.apk")
