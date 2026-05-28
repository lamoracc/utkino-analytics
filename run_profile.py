from pathlib import Path

from src.utkino.pipeline import run_profile


ROOT = Path(__file__).resolve().parent


if __name__ == "__main__":
    result = run_profile(
        input_file=ROOT / "Data" / "Utkino.xls",
        output_dir=ROOT / "outputs" / "profile",
    )
    print(f"Guests parsed: {result['summary']['guest_count']}")
    print(f"Total revenue: {result['summary']['total_revenue']:,.2f}")
    print(f"Profile saved: {result['profile_path']}")

