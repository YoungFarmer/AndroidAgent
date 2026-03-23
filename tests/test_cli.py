from android_agent.cli import _default_config_path, build_parser


def test_cli_accepts_aagent_commands() -> None:
    parser = build_parser()
    args = parser.parse_args(["run", "--case", "login_dialog_check"])
    assert args.command == "run"
    assert args.case == "login_dialog_check"


def test_default_config_path_is_repo_scoped() -> None:
    assert _default_config_path().name == "agent.example.yaml"
    assert _default_config_path().exists()
