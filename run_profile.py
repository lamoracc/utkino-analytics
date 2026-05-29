from pathlib import Path

from src.hotel_analytics.pipeline import run_profile


ROOT = Path(__file__).resolve().parent


def default_input_file() -> Path:
    data_dir = ROOT / "Data"
    candidates = sorted(data_dir.glob("*.xls*"))
    return candidates[0] if candidates else data_dir / "report.xlsx"


if __name__ == "__main__":
    result = run_profile(
        input_file=default_input_file(),
        output_dir=ROOT / "outputs" / "profile",
    )
    print(f"Guests parsed: {result['summary']['guest_count']}")
    print(f"Total revenue: {result['summary']['total_revenue']:,.2f}")
    print(f"Profile saved: {result['profile_path']}")
