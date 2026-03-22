from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass
class InstrumentationConfig:
    enabled: bool = False
    install_task: str = "installDebugAndroidTest"


@dataclass
class AppConfig:
    package_name: str
    launch_activity: str | None = None
    deep_link: str | None = None


@dataclass
class ExecutionConfig:
    default_executor: str = "maestro"
    maestro_bin: str = "maestro"
    adb_bin: str = "adb"
    java_bin: str = "java"


@dataclass
class OutputConfig:
    base_dir: Path = Path("outputs")
    runs_subdir: str = "runs"
    reports_subdir: str = "reports"

    @property
    def runs_dir(self) -> Path:
        return self.base_dir / self.runs_subdir

    @property
    def reports_dir(self) -> Path:
        return self.base_dir / self.reports_subdir


@dataclass
class ProjectConfig:
    project_path: Path
    gradle_command: str = "./gradlew"
    assemble_task: str = "assembleDebug"
    uninstall_before_install: bool = True
    install_retries: int = 1
    device_serial: str | None = None
    maestro_cases_dir: Path = Path("configs/cases")
    instrumentation: InstrumentationConfig = field(default_factory=InstrumentationConfig)
    app: AppConfig | None = None
    execution: ExecutionConfig = field(default_factory=ExecutionConfig)
    output: OutputConfig = field(default_factory=OutputConfig)


def _as_path(raw: str | None, *, base_dir: Path) -> Path | None:
    if raw is None:
        return None
    path = Path(raw)
    if not path.is_absolute():
        path = (base_dir / path).resolve()
    return path


def load_config(path: str | Path) -> ProjectConfig:
    config_path = Path(path).resolve()
    payload = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    base_dir = config_path.parent

    app_raw = payload.get("app") or {}
    exec_raw = payload.get("execution") or {}
    output_raw = payload.get("output") or {}
    instrumentation_raw = payload.get("instrumentation") or {}

    app = None
    if app_raw:
        app = AppConfig(
            package_name=app_raw["package_name"],
            launch_activity=app_raw.get("launch_activity"),
            deep_link=app_raw.get("deep_link"),
        )

    output = OutputConfig(
        base_dir=_as_path(output_raw.get("base_dir"), base_dir=base_dir) or (base_dir / "outputs").resolve(),
        runs_subdir=output_raw.get("runs_subdir", "runs"),
        reports_subdir=output_raw.get("reports_subdir", "reports"),
    )

    return ProjectConfig(
        project_path=_as_path(payload["project_path"], base_dir=base_dir) or Path("."),
        gradle_command=payload.get("gradle_command", "./gradlew"),
        assemble_task=payload.get("assemble_task", "assembleDebug"),
        uninstall_before_install=payload.get("uninstall_before_install", True),
        install_retries=int(payload.get("install_retries", 1)),
        device_serial=payload.get("device_serial"),
        maestro_cases_dir=_as_path(payload.get("maestro_cases_dir"), base_dir=base_dir) or (base_dir / "cases").resolve(),
        instrumentation=InstrumentationConfig(
            enabled=bool(instrumentation_raw.get("enabled", False)),
            install_task=instrumentation_raw.get("install_task", "installDebugAndroidTest"),
        ),
        app=app,
        execution=ExecutionConfig(
            default_executor=exec_raw.get("default_executor", "maestro"),
            maestro_bin=exec_raw.get("maestro_bin", "maestro"),
            adb_bin=exec_raw.get("adb_bin", "adb"),
            java_bin=exec_raw.get("java_bin", "java"),
        ),
        output=output,
    )


def load_case(case_path: str | Path) -> dict[str, Any]:
    return yaml.safe_load(Path(case_path).read_text(encoding="utf-8")) or {}
