from pathlib import Path

from android_agent.config import load_config
from android_agent.evidence import EvidenceCollector
from android_agent.executors.maestro import MaestroExecutor
from android_agent.models import CommandResult
from android_agent.utils import ensure_dir


class FakeRunner:
    def run(self, command, *, cwd=None, timeout=None):
        if "screencap" in command:
            return CommandResult(command, 0, "PNGDATA", "", 0.1)
        if "uiautomator" in command:
            return CommandResult(command, 0, "UI hierachy dumped", "", 0.1)
        if "pull" in command:
            return CommandResult(command, 0, "", "", 0.1)
        return CommandResult(command, 0, "ok", "", 0.1)


def test_maestro_builds_flow_and_returns_steps(tmp_path: Path) -> None:
    config = load_config(Path("configs/agent.example.yaml"))
    config.output.base_dir = tmp_path
    run_dir = ensure_dir(tmp_path / "run")
    case = {
        "name": "demo",
        "app_id": "com.example.app",
        "steps": [
            {"action": "launch"},
            {"action": "tap", "target": "登录按钮"},
            {"action": "assert_visible", "target": "首页"},
        ],
    }
    executor = MaestroExecutor(config, FakeRunner(), EvidenceCollector(config, FakeRunner(), run_dir))
    results = executor.run_case(case, run_dir)
    assert len(results) == 3
    assert (run_dir / "maestro-flow.yaml").exists()
    assert (run_dir / "test.log").exists()
