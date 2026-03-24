from pathlib import Path
import subprocess

from android_agent.shell import LocalCommandRunner


def test_local_command_runner_returns_command_result_when_cwd_is_missing(tmp_path: Path) -> None:
    runner = LocalCommandRunner()

    result = runner.run(["pwd"], cwd=tmp_path / "missing-project")

    assert result.returncode == 127
    assert "path was not found" in result.stderr


def test_local_command_runner_decodes_timeout_output() -> None:
    runner = LocalCommandRunner()

    def fake_run(*args, **kwargs):
        raise subprocess.TimeoutExpired(cmd=["adb", "logcat", "-c"], timeout=30, output=b"partial", stderr=b"device busy")

    original_run = subprocess.run
    subprocess.run = fake_run
    try:
        result = runner.run(["adb", "logcat", "-c"], timeout=30)
    finally:
        subprocess.run = original_run

    assert result.returncode == 124
    assert result.stdout == "partial"
    assert "device busy" in result.stderr
    assert "Command timed out after 30 seconds." in result.stderr
