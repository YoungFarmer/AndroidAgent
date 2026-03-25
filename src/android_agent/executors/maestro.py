from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from android_agent.config import ProjectConfig
from android_agent.evidence import EvidenceCollector
from android_agent.models import Status, StepResult
from android_agent.shell import CommandRunner
from android_agent.utils import ensure_dir


class MaestroExecutor:
    name = "maestro"

    def __init__(
        self,
        config: ProjectConfig,
        runner: CommandRunner,
        evidence: EvidenceCollector,
    ) -> None:
        self.config = config
        self.runner = runner
        self.evidence = evidence

    def _command_for_step(self, step: dict[str, Any]) -> dict[str, Any]:
        action = step["action"]
        if action == "launch":
            if self.config.app is None:
                raise ValueError("app config is required for launch steps")
            return {"launchApp": {"appId": self.config.app.package_name}}
        if action == "tap":
            return {"tapOn": step["target"]}
        if action == "input":
            return [{"tapOn": step["target"]}, {"inputText": step["value"]}]
        if action == "wait":
            return {"waitForAnimationToEnd": {"timeout": int(step.get("ms", 1000))}}
        if action == "assert_visible":
            return {"assertVisible": step["target"]}
        if action == "back":
            return {"pressKey": "BACK"}
        if action == "handle_permission":
            label = step.get("target", "允许|Allow|仅在使用中允许")
            return {"tapOn": {"textRegex": label, "optional": True}}
        raise ValueError(f"unsupported action: {action}")

    def build_flow(self, case: dict[str, Any], output_path: Path) -> Path:
        commands: list[Any] = []
        for step in case.get("steps", []):
            converted = self._command_for_step(step)
            if isinstance(converted, list):
                commands.extend(converted)
            else:
                commands.append(converted)
        flow_config = {"appId": case.get("app_id") or (self.config.app.package_name if self.config.app else "")}
        ensure_dir(output_path.parent)
        flow_text = (
            yaml.safe_dump(flow_config, sort_keys=False, allow_unicode=True).strip()
            + "\n---\n"
            + yaml.safe_dump(commands, sort_keys=False, allow_unicode=True)
        )
        output_path.write_text(flow_text, encoding="utf-8")
        return output_path

    def run_case(self, case: dict, run_dir: Path) -> list[StepResult]:
        flow_path = self.build_flow(case, run_dir / "maestro-flow.yaml")
        test_log = run_dir / "test.log"
        step_results: list[StepResult] = []

        for index, step in enumerate(case.get("steps", []), start=1):
            screenshot = None
            if step["action"] in {"launch", "assert_visible"}:
                screenshot = str(self.evidence.capture_screenshot(f"step_{index:02d}_before"))
            step_results.append(
                StepResult(
                    index=index,
                    action=step["action"],
                    target=step.get("target"),
                    status=Status.PASS,
                    message="planned for execution",
                    screenshot_path=screenshot,
                )
            )

        command = [self.config.execution.maestro_bin, "test", str(flow_path)]
        if self.config.device_serial:
            command.extend(["--device", self.config.device_serial])
        result = self.runner.run(command, timeout=1200)
        test_log.write_text(result.merged_output() + "\n", encoding="utf-8")

        if not result.ok and step_results:
            step_results[-1].status = Status.FAIL
            step_results[-1].message = "maestro execution failed"
            step_results[-1].screenshot_path = str(self.evidence.capture_screenshot(f"step_{step_results[-1].index:02d}_failed"))
            self.evidence.capture_ui_hierarchy(f"step_{step_results[-1].index:02d}_failed")
        elif not result.ok:
            step_results.append(StepResult(index=1, action="run", target=None, status=Status.FAIL, message="maestro execution failed"))
        else:
            if step_results:
                step_results[-1].screenshot_path = str(self.evidence.capture_screenshot(f"step_{step_results[-1].index:02d}_after"))
        self.evidence.add_event("executor", f"maestro run finished with exit_code={result.returncode}", {"flow": str(flow_path)})
        return step_results
