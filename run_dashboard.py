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
        summary_path = profile_dir / "summary.json"
        if not summary_path.exists():
            raise
        import json

        profile = {
            "summary": json.loads(summary_path.read_text(encoding="utf-8")),
        }
        print(f"Profile files are locked, using existing profile: {error}")

    output_path = build_dashboard(
        profile_dir=profile_dir,
        output_file=ROOT / "outputs" / "report.html",
    )
    print(f"Guests parsed: {profile['summary']['guest_count']}")
    print(f"Total revenue: {profile['summary']['total_revenue']:,.2f}")
    print(f"Dashboard saved: {output_path}")
