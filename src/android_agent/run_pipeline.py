from __future__ import annotations

from pathlib import Path

from android_agent.build_runner import run_build
from android_agent.config import ProjectConfig, load_case
from android_agent.device_manager import install_and_launch
from android_agent.doctor import enrich_device_info
from android_agent.evidence import EvidenceCollector
from android_agent.executors import MaestroExecutor
from android_agent.models import RunSummary, Status
from android_agent.reporter import write_run_report
from android_agent.shell import CommandRunner
from android_agent.utils import detect_git_ref, ensure_dir, utc_now


def make_run_id(prefix: str = "run") -> str:
    return f"{prefix}-{utc_now().replace(':', '').replace('+00:00', 'Z')}"


def execute_run(
    config: ProjectConfig,
    runner: CommandRunner,
    case_id: str,
    *,
    template_path: Path,
    run_id: str | None = None,
) -> RunSummary:
    case_path = config.maestro_cases_dir / f"{case_id}.yaml"
    case = load_case(case_path)
    current_run_id = run_id or make_run_id()
    run_dir = ensure_dir(config.output.runs_dir / current_run_id)
    evidence = EvidenceCollector(config=config, runner=runner, run_dir=run_dir)
    evidence.add_event("run", "run started", {"case_id": case_id})
    evidence.clear_logcat()

    build_result = run_build(config, runner, run_dir)
    install_result = None
    step_results = []
    status = build_result.status
    failure_reason = build_result.failure_reason

    if build_result.status is Status.PASS and build_result.apk_path:
        install_result = install_and_launch(
            config,
            runner,
            run_dir,
            Path(build_result.apk_path),
            deep_link=case.get("deep_link"),
        )
        status = install_result.status
        failure_reason = install_result.failure_reason

    if status is Status.PASS:
        executor = MaestroExecutor(config=config, runner=runner, evidence=evidence)
        step_results = executor.run_case(case, run_dir)
        if any(step.status is Status.FAIL for step in step_results):
            status = Status.FAIL
            failure_reason = next(step.message for step in step_results if step.status is Status.FAIL)

    logcat_path = evidence.collect_logcat()
    timeline_path = evidence.write_timeline()
    device = None
    if config.device_serial:
        device = enrich_device_info(runner, config.execution.adb_bin, config.device_serial)

    summary = RunSummary(
        run_id=current_run_id,
        task_name=case.get("name", case_id),
        status=status,
        case_id=case_id,
        device=device,
        git_ref=detect_git_ref(config.project_path),
        build_result=build_result,
        install_result=install_result,
        step_results=step_results,
        logcat_path=str(logcat_path),
        report_path=None,
        summary_path=None,
        timeline_path=str(timeline_path),
        evidence_paths=[str(logcat_path), str(timeline_path)],
        failure_reason=failure_reason,
    )
    summary_path, report_path = write_run_report(summary, template_path, run_dir)
    summary.summary_path = str(summary_path)
    summary.report_path = str(report_path)
    return summary


def execute_build_only(
    config: ProjectConfig,
    runner: CommandRunner,
    *,
    template_path: Path,
    run_id: str | None = None,
) -> RunSummary:
    current_run_id = run_id or make_run_id("build")
    run_dir = ensure_dir(config.output.runs_dir / current_run_id)
    evidence = EvidenceCollector(config=config, runner=runner, run_dir=run_dir)
    evidence.add_event("run", "build-only run started")
    evidence.clear_logcat()

    build_result = run_build(config, runner, run_dir)
    install_result = None
    status = build_result.status
    failure_reason = build_result.failure_reason

    if build_result.status is Status.PASS and build_result.apk_path and config.app is not None:
        install_result = install_and_launch(config, runner, run_dir, Path(build_result.apk_path))
        status = install_result.status
        failure_reason = install_result.failure_reason

    logcat_path = evidence.collect_logcat()
    timeline_path = evidence.write_timeline()
    device = None
    if config.device_serial:
        device = enrich_device_info(runner, config.execution.adb_bin, config.device_serial)

    summary = RunSummary(
        run_id=current_run_id,
        task_name="build_only",
        status=status,
        case_id=None,
        device=device,
        git_ref=detect_git_ref(config.project_path),
        build_result=build_result,
        install_result=install_result,
        step_results=[],
        logcat_path=str(logcat_path),
        report_path=None,
        summary_path=None,
        timeline_path=str(timeline_path),
        evidence_paths=[str(logcat_path), str(timeline_path)],
        failure_reason=failure_reason,
    )
    summary_path, report_path = write_run_report(summary, template_path, run_dir)
    summary.summary_path = str(summary_path)
    summary.report_path = str(report_path)
    return summary
