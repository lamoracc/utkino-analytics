from __future__ import annotations

import csv
import json
import subprocess
from collections import defaultdict
from pathlib import Path

from .parser import SERVICE_COLUMNS, guest_to_dict, parse_main_sheet


def export_excel_to_csv(input_file: Path, csv_dir: Path) -> None:
    script = Path(__file__).resolve().parents[2] / "scripts" / "export_excel_to_csv.ps1"
    subprocess.run(
        [
            "powershell",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(script),
            "-InputFile",
            str(input_file),
            "-OutputDir",
            str(csv_dir),
        ],
        check=True,
    )


def build_summary(guests: list) -> dict:
    total_revenue = sum(guest.total_revenue for guest in guests)
    room_revenue = sum(guest.room_revenue for guest in guests)
    nights = sum(guest.nights for guest in guests)
    arrivals = sum(guest.arrivals for guest in guests)
    repeat_guests = [guest for guest in guests if guest.arrivals > 1]

    by_segment = defaultdict(lambda: {"guests": 0, "revenue": 0.0, "nights": 0.0})
    by_city = defaultdict(lambda: {"guests": 0, "revenue": 0.0, "nights": 0.0})

    for guest in guests:
        by_segment[guest.segment]["guests"] += 1
        by_segment[guest.segment]["revenue"] += guest.total_revenue
        by_segment[guest.segment]["nights"] += guest.nights

        by_city[guest.city_normalized]["guests"] += 1
        by_city[guest.city_normalized]["revenue"] += guest.total_revenue
        by_city[guest.city_normalized]["nights"] += guest.nights

    service_totals = {
        field: sum(getattr(guest, field) for guest in guests)
        for field in SERVICE_COLUMNS
    }

    return {
        "guest_count": len(guests),
        "arrivals": arrivals,
        "nights": nights,
        "total_revenue": total_revenue,
        "room_revenue": room_revenue,
        "room_revenue_share": room_revenue / total_revenue if total_revenue else 0,
        "average_revenue_per_guest": total_revenue / len(guests) if guests else 0,
        "average_revenue_per_arrival": total_revenue / arrivals if arrivals else 0,
        "average_revenue_per_night": total_revenue / nights if nights else 0,
        "repeat_guest_count": len(repeat_guests),
        "repeat_guest_share": len(repeat_guests) / len(guests) if guests else 0,
        "repeat_revenue_share": (
            sum(guest.total_revenue for guest in repeat_guests) / total_revenue
            if total_revenue
            else 0
        ),
        "segments": sorted(
            by_segment.items(),
            key=lambda item: item[1]["revenue"],
            reverse=True,
        ),
        "top_cities": sorted(
            by_city.items(),
            key=lambda item: item[1]["revenue"],
            reverse=True,
        )[:25],
        "service_totals": sorted(
            service_totals.items(),
            key=lambda item: item[1],
            reverse=True,
        ),
    }


def write_clean_guests(guests: list, path: Path) -> None:
    rows = [guest_to_dict(guest) for guest in guests]
    if not rows:
        return

    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def run_profile(input_file: Path, output_dir: Path) -> dict:
    output_dir.mkdir(parents=True, exist_ok=True)
    csv_dir = output_dir / "csv"
    csv_dir.mkdir(parents=True, exist_ok=True)

    export_excel_to_csv(input_file=input_file, csv_dir=csv_dir)
    guests = parse_main_sheet(csv_dir)
    summary = build_summary(guests)

    clean_path = output_dir / "clean_guests.csv"
    profile_path = output_dir / "profile.json"

    write_clean_guests(guests, clean_path)
    profile_path.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    return {
        "summary": summary,
        "clean_path": str(clean_path),
        "profile_path": str(profile_path),
    }

