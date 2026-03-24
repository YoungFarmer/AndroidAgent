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
            stdout = _coerce_text(exc.stdout)
            stderr = _coerce_text(exc.stderr)
            return CommandResult(
                command=command,
                returncode=124,
                stdout=stdout,
                stderr=stderr + f"\nCommand timed out after {timeout} seconds.",
                duration_seconds=round(duration, 3),
            )
        except FileNotFoundError as exc:
            duration = time.perf_counter() - started
            missing_target = exc.filename or (str(cwd) if cwd else command[0])
            return CommandResult(
                command=command,
                returncode=127,
                stdout="",
                stderr=f"Command execution failed because path was not found: {missing_target}",
                duration_seconds=round(duration, 3),
            )
        except OSError as exc:
            duration = time.perf_counter() - started
            return CommandResult(
                command=command,
                returncode=126,
                stdout="",
                stderr=f"Command execution failed: {exc}",
                duration_seconds=round(duration, 3),
            )


def _coerce_text(value: str | bytes | None) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return value


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
