from android_agent.cli import build_parser


def test_cli_accepts_aagent_commands() -> None:
    parser = build_parser()
    args = parser.parse_args(["run", "--case", "login_dialog_check"])
    assert args.command == "run"
    assert args.case == "login_dialog_check"
