from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any


class Status(str, Enum):
    PASS = "PASS"
    WARN = "WARN"
    FAIL = "FAIL"


@dataclass
class DeviceInfo:
    serial: str
    state: str
    model: str | None = None
    android_version: str | None = None
    resolution: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class CheckResult:
    name: str
    status: Status
    message: str
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["status"] = self.status.value
        return data


@dataclass
class DoctorReport:
    generated_at: str
    overall_status: Status
    checks: list[CheckResult]
    devices: list[DeviceInfo]

    def to_dict(self) -> dict[str, Any]:
        return {
            "generated_at": self.generated_at,
            "overall_status": self.overall_status.value,
            "checks": [check.to_dict() for check in self.checks],
            "devices": [device.to_dict() for device in self.devices],
        }


@dataclass
class CommandResult:
    command: list[str]
    returncode: int
    stdout: str
    stderr: str
    duration_seconds: float

    @property
    def ok(self) -> bool:
        return self.returncode == 0

    def merged_output(self) -> str:
        parts = [self.stdout.strip(), self.stderr.strip()]
        return "\n".join(part for part in parts if part)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class BuildResult:
    status: Status
    task: str
    apk_path: str | None
    android_test_apk_path: str | None
    log_path: str
    command_result: CommandResult
    failure_reason: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status.value,
            "task": self.task,
            "apk_path": self.apk_path,
            "android_test_apk_path": self.android_test_apk_path,
            "log_path": self.log_path,
            "failure_reason": self.failure_reason,
            "command_result": self.command_result.to_dict(),
        }


@dataclass
class InstallResult:
    status: Status
    package_name: str
    serial: str
    install_log_path: str
    launch_log_path: str
    install_command_results: list[CommandResult]
    launch_command_result: CommandResult | None = None
    failure_reason: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status.value,
            "package_name": self.package_name,
            "serial": self.serial,
            "install_log_path": self.install_log_path,
            "launch_log_path": self.launch_log_path,
            "failure_reason": self.failure_reason,
            "install_command_results": [result.to_dict() for result in self.install_command_results],
            "launch_command_result": None if self.launch_command_result is None else self.launch_command_result.to_dict(),
        }


@dataclass
class StepResult:
    index: int
    action: str
    target: str | None
    status: Status
    message: str
    screenshot_path: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "index": self.index,
            "action": self.action,
            "target": self.target,
            "status": self.status.value,
            "message": self.message,
            "screenshot_path": self.screenshot_path,
        }


@dataclass
class TimelineEvent:
    timestamp: str
    category: str
    message: str
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class RunSummary:
    run_id: str
    task_name: str
    status: Status
    case_id: str | None
    device: DeviceInfo | None
    git_ref: str | None
    build_result: BuildResult | None
    install_result: InstallResult | None
    step_results: list[StepResult]
    logcat_path: str | None
    report_path: str | None
    summary_path: str | None
    timeline_path: str | None
    evidence_paths: list[str] = field(default_factory=list)
    failure_reason: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "task_name": self.task_name,
            "status": self.status.value,
            "case_id": self.case_id,
            "device": None if self.device is None else self.device.to_dict(),
            "git_ref": self.git_ref,
            "build_result": None if self.build_result is None else self.build_result.to_dict(),
            "install_result": None if self.install_result is None else self.install_result.to_dict(),
            "step_results": [step.to_dict() for step in self.step_results],
            "logcat_path": self.logcat_path,
            "report_path": self.report_path,
            "summary_path": self.summary_path,
            "timeline_path": self.timeline_path,
            "evidence_paths": self.evidence_paths,
            "failure_reason": self.failure_reason,
        }


def coerce_path(value: str | Path | None) -> str | None:
    if value is None:
        return None
    return str(Path(value))
