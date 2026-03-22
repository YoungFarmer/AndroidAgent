from __future__ import annotations

from pathlib import Path

from android_agent.models import DoctorReport, RunSummary
from android_agent.utils import load_template, write_json, write_text


def write_doctor_report(report: DoctorReport, reports_dir: Path) -> tuple[Path, Path]:
    json_path = reports_dir / f"doctor-{report.generated_at.replace(':', '-')}.json"
    md_path = reports_dir / f"doctor-{report.generated_at.replace(':', '-')}.md"
    write_json(json_path, report.to_dict())
    device_lines = [
        f"- {device.serial}: state={device.state}, model={device.model or 'unknown'}, "
        f"android={device.android_version or 'unknown'}, resolution={device.resolution or 'unknown'}"
        for device in report.devices
    ]
    if not device_lines:
        device_lines = ["- No connected devices detected."]
    markdown = "\n".join(
        [
            "# aagent doctor",
            "",
            f"- Overall status: {report.overall_status.value}",
            "",
            "## Checks",
            *[f"- [{check.status.value}] {check.name}: {check.message}" for check in report.checks],
            "",
            "## Devices",
            *device_lines,
            "",
        ]
    )
    write_text(md_path, markdown)
    return json_path, md_path


def write_run_report(summary: RunSummary, template_path: Path, run_dir: Path) -> tuple[Path, Path]:
    summary_path = run_dir / "summary.json"
    report_path = run_dir / "report.md"
    write_json(summary_path, summary.to_dict())

    template = load_template(template_path)
    content = template.substitute(
        run_id=summary.run_id,
        task_name=summary.task_name,
        status=summary.status.value,
        case_id=summary.case_id or "n/a",
        git_ref=summary.git_ref or "unknown",
        device_serial=summary.device.serial if summary.device else "unknown",
        device_model=summary.device.model if summary.device and summary.device.model else "unknown",
        device_android=summary.device.android_version if summary.device and summary.device.android_version else "unknown",
        build_status=summary.build_result.status.value if summary.build_result else "SKIPPED",
        install_status=summary.install_result.status.value if summary.install_result else "SKIPPED",
        failure_reason=summary.failure_reason or "none",
        logcat_path=summary.logcat_path or "n/a",
        evidence_paths="\n".join(f"- {item}" for item in summary.evidence_paths) or "- none",
        step_results="\n".join(
            f"- [{step.status.value}] step {step.index} {step.action} {step.target or ''}: {step.message}".rstrip()
            for step in summary.step_results
        )
        or "- no steps executed",
    )
    write_text(report_path, content)
    return summary_path, report_path
