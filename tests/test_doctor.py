from pathlib import Path

from android_agent.config import load_config
from android_agent.doctor import run_doctor
from android_agent.models import CommandResult, Status


class FakeRunner:
    def run(self, command, *, cwd=None, timeout=None):
        if command[:3] == ["adb", "devices", "-l"]:
            return CommandResult(command, 0, "List of devices attached\nemulator-5554 device model:Pixel_8\n", "", 0.1)
        if "ro.build.version.release" in command:
            return CommandResult(command, 0, "14\n", "", 0.1)
        if "ro.product.model" in command:
            return CommandResult(command, 0, "Pixel 8\n", "", 0.1)
        if "wm" in command:
            return CommandResult(command, 0, "Physical size: 1080x2400\n", "", 0.1)
        return CommandResult(command, 0, "", "", 0.1)


def test_doctor_detects_connected_device() -> None:
    config = load_config(Path("configs/agent.example.yaml"))
    report = run_doctor(config, FakeRunner())
    assert any(check.name == "project_path" and check.status is Status.FAIL for check in report.checks)
    assert report.devices[0].serial == "emulator-5554"
    assert report.devices[0].android_version == "14"
    assert any(check.name == "connected_devices" and check.status in {Status.PASS, Status.WARN} for check in report.checks)
