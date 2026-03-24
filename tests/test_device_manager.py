from pathlib import Path

from android_agent.config import load_config
from android_agent.device_manager import install_and_launch
from android_agent.models import CommandResult, Status


class FakeDeviceRunner:
    def __init__(self) -> None:
        self.commands: list[list[str]] = []
        self.install_attempts = 0
        self.launch_attempts = 0

    def run(self, command, *, cwd=None, timeout=None):
        self.commands.append(command)
        if " install " in f" {' '.join(command)} ":
            self.install_attempts += 1
            if self.install_attempts == 1:
                return CommandResult(command, 1, "", "INSTALL_FAILED_UPDATE_INCOMPATIBLE", 0.1)
            return CommandResult(command, 0, "Success", "", 0.1)
        if command[-2:] == ["uninstall", "com.example.app"]:
            return CommandResult(command, 0, "Success", "", 0.1)
        if command[-2:] == ["uninstall", "com.example.app.test"]:
            return CommandResult(command, 0, "Success", "", 0.1)
        if command[:7] == ["adb", "-s", "emulator-5554", "shell", "am", "start", "-W"]:
            self.launch_attempts += 1
            if self.launch_attempts == 1:
                return CommandResult(command, 1, "", "Activity not started", 0.1)
            return CommandResult(command, 0, "Status: ok", "", 0.1)
        return CommandResult(command, 0, "ok", "", 0.1)


def test_install_and_launch_retries_and_uses_case_deep_link(tmp_path: Path) -> None:
    apk_path = tmp_path / "app-debug.apk"
    apk_path.write_text("apk", encoding="utf-8")
    run_dir = tmp_path / "run"
    run_dir.mkdir()

    config = load_config(Path("configs/agent.example.yaml"))
    config.instrumentation.enabled = True

    runner = FakeDeviceRunner()
    result = install_and_launch(
        config,
        runner,
        run_dir,
        apk_path,
        deep_link="myapp://details/42",
    )

    assert result.status is Status.PASS
    assert runner.install_attempts == 2
    assert runner.launch_attempts == 2
    assert ["adb", "-s", "emulator-5554", "uninstall", "com.example.app"] in runner.commands
    assert ["adb", "-s", "emulator-5554", "uninstall", "com.example.app.test"] in runner.commands
    assert any(command[-1] == "myapp://details/42" for command in runner.commands if "am" in command)
    assert "INSTALL_FAILED_UPDATE_INCOMPATIBLE" in (run_dir / "install.log").read_text(encoding="utf-8")
