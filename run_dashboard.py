from pathlib import Path

from src.utkino.pipeline import run_profile
from src.utkino.report import build_dashboard


ROOT = Path(__file__).resolve().parent


if __name__ == "__main__":
    profile_dir = ROOT / "outputs" / "profile"
    try:
        profile = run_profile(
            input_file=ROOT / "Data" / "Utkino.xls",
            output_dir=profile_dir,
        )
    except PermissionError as error:
        raise SystemExit(
            "Не удалось обновить данные отчета: один из файлов в outputs/profile "
            "заблокирован. Закройте Excel, браузерную загрузку, проводник с предпросмотром "
            "или синхронизацию, которая держит CSV/JSON, и запустите команду снова. "
            f"Техническая деталь: {error}"
        ) from error

    output_path = build_dashboard(
        profile_dir=profile_dir,
        output_file=ROOT / "outputs" / "report.html",
    )
    print(f"Guests parsed: {profile['summary']['guest_count']}")
    print(f"Total revenue: {profile['summary']['total_revenue']:,.2f}")
    print(f"Dashboard saved: {output_path}")
