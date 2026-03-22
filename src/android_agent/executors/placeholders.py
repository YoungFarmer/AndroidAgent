from __future__ import annotations

from pathlib import Path

from android_agent.models import Status, StepResult


class EspressoExecutor:
    name = "espresso"

    def run_case(self, case: dict, run_dir: Path) -> list[StepResult]:
        return [
            StepResult(
                index=0,
                action="executor",
                target=None,
                status=Status.WARN,
                message="Espresso executor is reserved for a later milestone.",
            )
        ]


class UiAutomatorExecutor:
    name = "uiautomator"

    def run_case(self, case: dict, run_dir: Path) -> list[StepResult]:
        return [
            StepResult(
                index=0,
                action="executor",
                target=None,
                status=Status.WARN,
                message="UI Automator executor is reserved for a later milestone.",
            )
        ]
