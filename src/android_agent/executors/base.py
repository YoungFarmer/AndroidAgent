from __future__ import annotations

from pathlib import Path
from typing import Protocol

from android_agent.models import StepResult


class Executor(Protocol):
    name: str

    def run_case(self, case: dict, run_dir: Path) -> list[StepResult]:
        """Execute the case and return step results."""
