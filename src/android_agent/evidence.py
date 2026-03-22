from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

from android_agent.config import ProjectConfig
from android_agent.models import TimelineEvent
from android_agent.shell import CommandRunner
from android_agent.utils import ensure_dir, utc_now


@dataclass
class EvidenceCollector:
    config: ProjectConfig
    runner: CommandRunner
    run_dir: Path
    timeline: list[TimelineEvent] = field(default_factory=list)

    def __post_init__(self) -> None:
        ensure_dir(self.run_dir / "screenshots")
        ensure_dir(self.run_dir / "hierarchy")

    def _adb_prefix(self) -> list[str]:
        prefix = [self.config.execution.adb_bin]
        if self.config.device_serial:
            prefix.extend(["-s", self.config.device_serial])
        return prefix

    def add_event(self, category: str, message: str, metadata: dict[str, str] | None = None) -> None:
        self.timeline.append(TimelineEvent(timestamp=utc_now(), category=category, message=message, metadata=metadata or {}))

    def clear_logcat(self) -> None:
        result = self.runner.run([*self._adb_prefix(), "logcat", "-c"], timeout=30)
        self.add_event("logcat", "cleared device logcat", {"ok": str(result.ok)})

    def collect_logcat(self) -> Path:
        output = self.run_dir / "logcat.txt"
        result = self.runner.run([*self._adb_prefix(), "logcat", "-d"], timeout=60)
        output.write_text(result.merged_output() + "\n", encoding="utf-8")
        self.add_event("logcat", "collected logcat", {"path": str(output)})
        return output

    def capture_screenshot(self, name: str) -> Path:
        output = self.run_dir / "screenshots" / f"{name}.png"
        try:
            completed = subprocess.run(
                [*self._adb_prefix(), "exec-out", "screencap", "-p"],
                check=False,
                capture_output=True,
                timeout=60,
            )
            output.write_bytes(completed.stdout)
            ok = completed.returncode == 0
        except OSError as exc:
            output.write_text(str(exc) + "\n", encoding="utf-8")
            ok = False
        self.add_event("screenshot", f"captured screenshot {name}", {"path": str(output), "ok": str(ok)})
        return output

    def capture_ui_hierarchy(self, name: str) -> Path:
        remote = f"/sdcard/{name}.xml"
        local = self.run_dir / "hierarchy" / f"{name}.xml"
        dump_result = self.runner.run([*self._adb_prefix(), "shell", "uiautomator", "dump", remote], timeout=60)
        pull_result = self.runner.run([*self._adb_prefix(), "pull", remote, str(local)], timeout=60)
        if not pull_result.ok:
            local.write_text(dump_result.merged_output() + "\n" + pull_result.merged_output(), encoding="utf-8")
        self.add_event("hierarchy", f"captured hierarchy {name}", {"path": str(local)})
        return local

    def write_timeline(self) -> Path:
        output = self.run_dir / "timeline.json"
        output.write_text(json.dumps([event.to_dict() for event in self.timeline], indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        return output
