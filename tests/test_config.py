from pathlib import Path

from android_agent.config import load_config


def test_load_config_resolves_paths() -> None:
    config = load_config(Path("configs/agent.example.yaml"))
    assert config.project_path.name == "sample-android-project"
    assert config.maestro_cases_dir.name == "cases"
    assert config.output.base_dir.name == "outputs"
    assert config.app is not None
    assert config.app.package_name == "com.example.app"
