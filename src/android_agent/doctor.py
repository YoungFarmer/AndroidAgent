from __future__ import annotations

import os
import shutil
from pathlib import Path

from android_agent.config import ProjectConfig
from android_agent.models import CheckResult, DeviceInfo, DoctorReport, Status
from android_agent.shell import CommandRunner
from android_agent.utils import utc_now


def _status_from_checks(checks: list[CheckResult]) -> Status:
    if any(check.status is Status.FAIL for check in checks):
        return Status.FAIL
    if any(check.status is Status.WARN for check in checks):
        return Status.WARN
    return Status.PASS


def _detect_devices(runner: CommandRunner, adb_bin: str) -> list[DeviceInfo]:
    result = runner.run([adb_bin, "devices", "-l"], timeout=15)
    if not result.ok:
        return []

    devices: list[DeviceInfo] = []
    for line in result.stdout.splitlines():
        if not line.strip() or line.startswith("List of devices attached"):
            continue
        tokens = line.split()
        if len(tokens) < 2:
            continue
        serial = tokens[0]
        state = tokens[1]
        model = None
        for token in tokens[2:]:
            if token.startswith("model:"):
                model = token.split(":", 1)[1]
        devices.append(DeviceInfo(serial=serial, state=state, model=model))
    return devices


def enrich_device_info(runner: CommandRunner, adb_bin: str, serial: str) -> DeviceInfo:
    base = ["-s", serial]
    version = runner.run([adb_bin, *base, "shell", "getprop", "ro.build.version.release"], timeout=10).stdout.strip() or None
    model = runner.run([adb_bin, *base, "shell", "getprop", "ro.product.model"], timeout=10).stdout.strip() or None
    size_raw = runner.run([adb_bin, *base, "shell", "wm", "size"], timeout=10).stdout.strip()
    resolution = None
    if ":" in size_raw:
        resolution = size_raw.split(":", 1)[1].strip()
    return DeviceInfo(serial=serial, state="device", model=model, android_version=version, resolution=resolution)


def run_doctor(config: ProjectConfig, runner: CommandRunner) -> DoctorReport:
    checks: list[CheckResult] = []
    bins = {
        "java": config.execution.java_bin,
        "adb": config.execution.adb_bin,
        "maestro": config.execution.maestro_bin,
    }
    for name, binary in bins.items():
        resolved = shutil.which(binary)
        status = Status.PASS if resolved else Status.FAIL
        message = resolved if resolved else f"{binary} not found in PATH"
        checks.append(CheckResult(name=f"{name}_binary", status=status, message=message))

    gradle_path = config.project_path / config.gradle_command
    gradle_available = gradle_path.exists() or shutil.which(config.gradle_command)
    checks.append(
        CheckResult(
            name="gradle_command",
            status=Status.PASS if gradle_available else Status.FAIL,
            message=str(gradle_path if gradle_path.exists() else config.gradle_command),
        )
    )

    sdk_path = os.environ.get("ANDROID_SDK_ROOT") or os.environ.get("ANDROID_HOME")
    checks.append(
        CheckResult(
            name="android_sdk",
            status=Status.PASS if sdk_path else Status.WARN,
            message=sdk_path or "ANDROID_SDK_ROOT / ANDROID_HOME not set",
        )
    )

    devices = _detect_devices(runner, config.execution.adb_bin)
    checks.append(
        CheckResult(
            name="connected_devices",
            status=Status.PASS if devices else Status.WARN,
            message=f"{len(devices)} device(s) detected",
        )
    )

    if config.app is None:
        checks.append(CheckResult(name="app_config", status=Status.FAIL, message="app config is missing"))
    else:
        launch_ok = bool(config.app.launch_activity or config.app.deep_link)
        checks.append(
            CheckResult(
                name="app_config",
                status=Status.PASS if launch_ok else Status.WARN,
                message=f"package={config.app.package_name}, launch={'configured' if launch_ok else 'missing'}",
                details={
                    "package_name": config.app.package_name,
                    "launch_activity": config.app.launch_activity,
                    "deep_link": config.app.deep_link,
                },
            )
        )

    if config.device_serial:
        matched = next((device for device in devices if device.serial == config.device_serial), None)
        checks.append(
            CheckResult(
                name="target_device",
                status=Status.PASS if matched else Status.WARN,
                message=config.device_serial if matched else f"configured serial {config.device_serial} not connected",
            )
        )

    detailed_devices = [
        enrich_device_info(runner, config.execution.adb_bin, device.serial) if device.state == "device" else device
        for device in devices
    ]
    return DoctorReport(
        generated_at=utc_now(),
        overall_status=_status_from_checks(checks),
        checks=checks,
        devices=detailed_devices,
    )


def render_doctor_markdown(report: DoctorReport) -> str:
    lines = [
        "# aagent doctor",
        "",
        f"- Generated at: {report.generated_at}",
        f"- Overall status: {report.overall_status.value}",
        "",
        "## Checks",
    ]
    for check in report.checks:
        lines.append(f"- [{check.status.value}] {check.name}: {check.message}")
    lines.extend(["", "## Devices"])
    if not report.devices:
        lines.append("- No connected devices detected.")
    else:
        for device in report.devices:
            lines.append(
                f"- {device.serial}: state={device.state}, model={device.model or 'unknown'}, "
                f"android={device.android_version or 'unknown'}, resolution={device.resolution or 'unknown'}"
            )
    lines.append("")
    return "\n".join(lines)
