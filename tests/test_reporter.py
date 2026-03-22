from pathlib import Path

from android_agent.models import DeviceInfo, RunSummary, Status
from android_agent.reporter import write_run_report


def test_write_run_report_creates_summary_and_markdown(tmp_path: Path) -> None:
    summary = RunSummary(
        run_id="run-1",
        task_name="demo",
        status=Status.PASS,
        case_id="demo",
        device=DeviceInfo(serial="emulator-5554", state="device", model="Pixel", android_version="14", resolution="1080x2400"),
        git_ref="abc123",
        build_result=None,
        install_result=None,
        step_results=[],
        logcat_path="logcat.txt",
        report_path=None,
        summary_path=None,
        timeline_path="timeline.json",
        evidence_paths=["logcat.txt", "timeline.json"],
        failure_reason=None,
    )
    summary_path, report_path = write_run_report(summary, Path("templates/report.md.j2"), tmp_path)
    assert summary_path.exists()
    assert report_path.exists()
    assert "run-1" in report_path.read_text(encoding="utf-8")
