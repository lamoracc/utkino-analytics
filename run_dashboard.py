from pathlib import Path

from src.utkino.generator import build_report_from_excel, make_report_dir


ROOT = Path(__file__).resolve().parent


if __name__ == "__main__":
    result = build_report_from_excel(
        input_file=ROOT / "Data" / "Utkino.xls",
        report_dir=make_report_dir(ROOT / "reports"),
    )
    print(f"Guests parsed: {result['summary']['guest_count']}")
    print(f"Total revenue: {result['summary']['total_revenue']:,.2f}")
    print(f"Dashboard saved: {result['output_path']}")
