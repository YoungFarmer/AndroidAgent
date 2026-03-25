from __future__ import annotations

import base64
import csv
import hashlib
import os
from pathlib import Path
from tempfile import TemporaryDirectory
import tomllib
from zipfile import ZIP_DEFLATED, ZipFile


ROOT = Path(__file__).resolve().parent


def _load_project_table() -> dict:
    with (ROOT / "pyproject.toml").open("rb") as fh:
        return tomllib.load(fh)


def _distribution_name(name: str) -> str:
    return name.replace("-", "_")


def _dist_info_dir(project_name: str, version: str) -> str:
    return f"{_distribution_name(project_name)}-{version}.dist-info"


def _wheel_name(project_name: str, version: str) -> str:
    return f"{_distribution_name(project_name)}-{version}-py3-none-any.whl"


def _metadata_text(pyproject: dict) -> str:
    project = pyproject["project"]
    lines = [
        "Metadata-Version: 2.1",
        f"Name: {project['name']}",
        f"Version: {project['version']}",
    ]
    description = project.get("description")
    if description:
        lines.append(f"Summary: {description}")
    readme = project.get("readme")
    if isinstance(readme, str):
        lines.append("Description-Content-Type: text/markdown")
    python_requires = project.get("requires-python")
    if python_requires:
        lines.append(f"Requires-Python: {python_requires}")
    for requirement in project.get("dependencies", []):
        lines.append(f"Requires-Dist: {requirement}")
    lines.extend(["", ""])

    if isinstance(readme, str):
        readme_path = ROOT / readme
        if readme_path.exists():
            lines.append(readme_path.read_text(encoding="utf-8"))
    return "\n".join(lines)


def _entry_points_text(pyproject: dict) -> str:
    scripts = pyproject.get("project", {}).get("scripts", {})
    if not scripts:
        return ""
    lines = ["[console_scripts]"]
    for name, target in scripts.items():
        lines.append(f"{name} = {target}")
    lines.append("")
    return "\n".join(lines)


def _wheel_text() -> str:
    return "\n".join(
        [
            "Wheel-Version: 1.0",
            "Generator: packaging_backend",
            "Root-Is-Purelib: true",
            "Tag: py3-none-any",
            "",
        ]
    )


def _iter_package_files(src_root: Path):
    for path in sorted(src_root.rglob("*")):
        if path.is_file():
            yield path, path.relative_to(src_root).as_posix()


def _record_line(path: str, content: bytes) -> list[str]:
    digest = hashlib.sha256(content).digest()
    encoded = base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")
    return [path, f"sha256={encoded}", str(len(content))]


def _write_metadata(metadata_directory: str, pyproject: dict) -> str:
    project = pyproject["project"]
    dist_info = Path(metadata_directory) / _dist_info_dir(project["name"], project["version"])
    dist_info.mkdir(parents=True, exist_ok=True)
    (dist_info / "METADATA").write_text(_metadata_text(pyproject), encoding="utf-8")
    entry_points = _entry_points_text(pyproject)
    if entry_points:
        (dist_info / "entry_points.txt").write_text(entry_points, encoding="utf-8")
    (dist_info / "WHEEL").write_text(_wheel_text(), encoding="utf-8")
    return dist_info.name


def _build_wheel_impl(wheel_directory: str, editable: bool) -> str:
    pyproject = _load_project_table()
    project = pyproject["project"]
    wheel_name = _wheel_name(project["name"], project["version"])
    dist_info_dir = _dist_info_dir(project["name"], project["version"])
    src_root = ROOT / pyproject["tool"]["setuptools"]["package-dir"][""]
    wheel_path = Path(wheel_directory) / wheel_name

    records: list[list[str]] = []
    with ZipFile(wheel_path, "w", compression=ZIP_DEFLATED) as zf:
        if editable:
            pth_name = f"{_distribution_name(project['name'])}.pth"
            pth_content = f"{src_root}\n".encode("utf-8")
            zf.writestr(pth_name, pth_content)
            records.append(_record_line(pth_name, pth_content))
        else:
            for source_path, archive_path in _iter_package_files(src_root):
                content = source_path.read_bytes()
                zf.writestr(archive_path, content)
                records.append(_record_line(archive_path, content))

        metadata_content = _metadata_text(pyproject).encode("utf-8")
        metadata_path = f"{dist_info_dir}/METADATA"
        zf.writestr(metadata_path, metadata_content)
        records.append(_record_line(metadata_path, metadata_content))

        wheel_content = _wheel_text().encode("utf-8")
        wheel_file_path = f"{dist_info_dir}/WHEEL"
        zf.writestr(wheel_file_path, wheel_content)
        records.append(_record_line(wheel_file_path, wheel_content))

        entry_points = _entry_points_text(pyproject)
        if entry_points:
            entry_points_content = entry_points.encode("utf-8")
            entry_points_path = f"{dist_info_dir}/entry_points.txt"
            zf.writestr(entry_points_path, entry_points_content)
            records.append(_record_line(entry_points_path, entry_points_content))

        record_path = f"{dist_info_dir}/RECORD"
        with TemporaryDirectory() as tmpdir:
            record_file = Path(tmpdir) / "RECORD"
            with record_file.open("w", encoding="utf-8", newline="") as fh:
                writer = csv.writer(fh)
                writer.writerows(records)
                writer.writerow([record_path, "", ""])
            record_content = record_file.read_bytes()
        zf.writestr(record_path, record_content)

    return wheel_name


def _supported_features() -> list[str]:
    return ["build_editable"]


def get_requires_for_build_wheel(config_settings=None) -> list[str]:
    return []


def get_requires_for_build_editable(config_settings=None) -> list[str]:
    return []


def prepare_metadata_for_build_wheel(metadata_directory: str, config_settings=None) -> str:
    return _write_metadata(metadata_directory, _load_project_table())


def prepare_metadata_for_build_editable(metadata_directory: str, config_settings=None) -> str:
    return _write_metadata(metadata_directory, _load_project_table())


def build_wheel(
    wheel_directory: str,
    config_settings=None,
    metadata_directory: str | None = None,
) -> str:
    os.makedirs(wheel_directory, exist_ok=True)
    return _build_wheel_impl(wheel_directory, editable=False)


def build_editable(
    wheel_directory: str,
    config_settings=None,
    metadata_directory: str | None = None,
) -> str:
    os.makedirs(wheel_directory, exist_ok=True)
    return _build_wheel_impl(wheel_directory, editable=True)
