from __future__ import annotations

import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from android_agent.models import CommandResult
from android_agent.utils import ensure_dir


class CommandRunner(Protocol):
    def run(
        self,
        command: list[str],
        *,
        cwd: Path | None = None,
        timeout: int | None = None,
    ) -> CommandResult: ...


@dataclass
class LocalCommandRunner:
    def run(
        self,
        command: list[str],
        *,
        cwd: Path | None = None,
        timeout: int | None = None,
    ) -> CommandResult:
        started = time.perf_counter()
        try:
            completed = subprocess.run(
                command,
                cwd=str(cwd) if cwd else None,
                check=False,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            duration = time.perf_counter() - started
            return CommandResult(
                command=command,
                returncode=completed.returncode,
                stdout=completed.stdout,
                stderr=completed.stderr,
                duration_seconds=round(duration, 3),
            )
        except subprocess.TimeoutExpired as exc:
            duration = time.perf_counter() - started
            return CommandResult(
                command=command,
                returncode=124,
                stdout=exc.stdout or "",
                stderr=(exc.stderr or "") + f"\nCommand timed out after {timeout} seconds.",
                duration_seconds=round(duration, 3),
            )


def persist_command_result(path: Path, result: CommandResult) -> Path:
    ensure_dir(path.parent)
    content = [
        f"$ {' '.join(result.command)}",
        "",
        "STDOUT:",
        result.stdout.rstrip(),
        "",
        "STDERR:",
        result.stderr.rstrip(),
        "",
        f"exit_code={result.returncode}",
        f"duration_seconds={result.duration_seconds}",
    ]
    path.write_text("\n".join(content).strip() + "\n", encoding="utf-8")
    return path
