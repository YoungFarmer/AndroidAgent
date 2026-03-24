from pathlib import Path

from android_agent.config import load_config


def test_load_config_resolves_paths() -> None:
    config = load_config(Path("configs/agent.example.yaml"))
    assert config.project_path.name == "sample-android-project"
    assert config.maestro_cases_dir.name == "cases"
    assert config.output.base_dir.name == "outputs"
    assert config.app is not None
    assert config.app.package_name == "com.example.app"
    assert config.app.test_package_name == "com.example.app.test"
    assert config.build_retries == 2
    assert config.launch_retries == 2


def test_load_config_expands_environment_variables(tmp_path: Path, monkeypatch) -> None:
    android_project = tmp_path / "sunflower"
    android_project.mkdir()
    config_path = tmp_path / "env-config.yaml"
    config_path.write_text(
        "\n".join(
            [
                "project_path: ${ANDROID_PROJECT_PATH}",
                "maestro_cases_dir: ./cases",
                "",
            ]
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("ANDROID_PROJECT_PATH", str(android_project))

    config = load_config(config_path)

    assert config.project_path == android_project.resolve()
    assert config.maestro_cases_dir == (tmp_path / "cases").resolve()
