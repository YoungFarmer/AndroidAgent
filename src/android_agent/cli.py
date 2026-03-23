from __future__ import annotations

import argparse
from pathlib import Path

from android_agent.config import load_config
from android_agent.doctor import run_doctor
from android_agent.reporter import write_doctor_report
from android_agent.run_pipeline import execute_build_only, execute_run, make_run_id
from android_agent.shell import LocalCommandRunner
from android_agent.utils import ensure_dir, project_path


def _default_config_path() -> Path:
    return project_path("configs", "agent.example.yaml")


def _report_template_path() -> Path:
    return project_path("templates", "report.md.j2")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="aagent", description="Standalone Android automation agent CLI.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    for command_name in ("doctor", "build"):
        command = subparsers.add_parser(command_name)
        command.add_argument("--config", type=Path, default=_default_config_path())

    run_command = subparsers.add_parser("run")
    run_command.add_argument("--config", type=Path, default=_default_config_path())
    run_command.add_argument("--case", required=True)
    run_command.add_argument("--run-id")

    report_command = subparsers.add_parser("report")
    report_command.add_argument("--config", type=Path, default=_default_config_path())
    report_command.add_argument("--run-id", required=True)
    return parser


def _print_doctor_summary(json_path: Path, md_path: Path, overall_status: str) -> None:
    print(f"aagent doctor completed with status={overall_status}")
    print(f"JSON report: {json_path}")
    print(f"Markdown report: {md_path}")


def _print_run_summary(summary) -> None:
    print(f"run_id={summary.run_id}")
    print(f"status={summary.status.value}")
    if summary.report_path:
        print(f"report={summary.report_path}")
    if summary.summary_path:
        print(f"summary={summary.summary_path}")
    if summary.failure_reason:
        print(f"failure_reason={summary.failure_reason}")


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    runner = LocalCommandRunner()
    config = load_config(args.config)
    ensure_dir(config.output.base_dir)
    ensure_dir(config.output.runs_dir)
    ensure_dir(config.output.reports_dir)

    if args.command == "doctor":
        report = run_doctor(config, runner)
        json_path, md_path = write_doctor_report(report, config.output.reports_dir)
        _print_doctor_summary(json_path, md_path, report.overall_status.value)
        return 0 if report.overall_status.value != "FAIL" else 1

    if args.command == "build":
        summary = execute_build_only(
            config,
            runner,
            template_path=_report_template_path(),
            run_id=args.command + "-" + make_run_id("manual"),
        )
        _print_run_summary(summary)
        return 0 if summary.status.value != "FAIL" else 1

    if args.command == "run":
        summary = execute_run(
            config,
            runner,
            case_id=args.case,
            template_path=_report_template_path(),
            run_id=args.run_id,
        )
        _print_run_summary(summary)
        return 0 if summary.status.value != "FAIL" else 1

    if args.command == "report":
        run_dir = config.output.runs_dir / args.run_id
        report_path = run_dir / "report.md"
        summary_path = run_dir / "summary.json"
        print(f"report={report_path}")
        print(f"summary={summary_path}")
        return 0

    parser.error(f"unsupported command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
