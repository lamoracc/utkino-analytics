from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from .pipeline import run_profile
from .report import build_dashboard


def make_report_dir(base_dir: Path, now: datetime | None = None) -> Path:
    timestamp = (now or datetime.now()).strftime("%Y-%m-%d_%H-%M-%S")
    return base_dir / timestamp


def build_report_from_excel(input_file: Path, report_dir: Path) -> dict:
    input_file = input_file.resolve()
    report_dir.mkdir(parents=True, exist_ok=True)

    profile_dir = report_dir / "profile"
    output_file = report_dir / "report.html"
    generated_at = datetime.now()

    try:
        profile = run_profile(input_file=input_file, output_dir=profile_dir)
    except PermissionError as error:
        raise RuntimeError(
            "Не удалось обновить данные отчета: один из файлов результата заблокирован. "
            "Закройте Excel, браузерную загрузку, проводник с предпросмотром или "
            "синхронизацию, которая держит CSV/JSON, и запустите генерацию снова."
        ) from error

    metadata = {
        "input_file_name": input_file.name,
        "input_file_path": str(input_file),
        "input_file_modified_at": datetime.fromtimestamp(
            input_file.stat().st_mtime
        ).isoformat(timespec="seconds"),
        "generated_at": generated_at.isoformat(timespec="seconds"),
    }

    output_path = build_dashboard(
        profile_dir=profile_dir,
        output_file=output_file,
        metadata=metadata,
    )
    (report_dir / "report_metadata.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    return {
        "summary": profile["summary"],
        "report_dir": str(report_dir),
        "output_path": str(output_path),
        "metadata": metadata,
    }
