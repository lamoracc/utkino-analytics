from __future__ import annotations

import csv
import json
import subprocess
from collections import defaultdict
from pathlib import Path

from .parser import SERVICE_COLUMNS, guest_to_dict, parse_main_sheet


SERVICE_LABELS = {
    "booking_room_sum": "Бронирование номера",
    "restaurant_spend": "Ресторан",
    "spa_spend": "SPA и БК",
    "fishing_spend": "Рыбалка",
    "laundry_spend": "Прачечная",
    "techpark_spend": "Технопарк",
    "horse_club_spend": "Конный клуб",
    "cap_spend": "Кепка",
    "transfer_spend": "Трансфер",
    "pets_spend": "Проживание животных",
}


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
        by_segment[guest.segment_label]["guests"] += 1
        by_segment[guest.segment_label]["revenue"] += guest.total_revenue
        by_segment[guest.segment_label]["nights"] += guest.nights

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


def aggregate_rows(guests: list, key_fields: list[str]) -> list[dict]:
    grouped = defaultdict(
        lambda: {
            "guests": 0,
            "arrivals": 0,
            "nights": 0.0,
            "room_revenue": 0.0,
            "total_revenue": 0.0,
            "extra_revenue": 0.0,
            "repeat_guests": 0,
        }
    )

    for guest in guests:
        key = tuple(getattr(guest, field) for field in key_fields)
        row = grouped[key]
        row["guests"] += 1
        row["arrivals"] += guest.arrivals
        row["nights"] += guest.nights
        row["room_revenue"] += guest.room_revenue
        row["total_revenue"] += guest.total_revenue
        row["extra_revenue"] += guest.extra_revenue
        row["repeat_guests"] += int(guest.is_repeat_guest)

    rows = []
    for key, metrics in grouped.items():
        row = dict(zip(key_fields, key))
        row.update(metrics)
        row["average_revenue_per_guest"] = (
            row["total_revenue"] / row["guests"] if row["guests"] else 0.0
        )
        row["average_revenue_per_night"] = (
            row["total_revenue"] / row["nights"] if row["nights"] else 0.0
        )
        row["repeat_guest_share"] = (
            row["repeat_guests"] / row["guests"] if row["guests"] else 0.0
        )
        rows.append(row)

    return sorted(rows, key=lambda item: item["total_revenue"], reverse=True)


def build_service_spend(guests: list) -> list[dict]:
    rows = []
    total_revenue = sum(guest.total_revenue for guest in guests)

    for field in SERVICE_COLUMNS:
        value = sum(getattr(guest, field) for guest in guests)
        filled_guests = sum(1 for guest in guests if getattr(guest, field) > 0)
        rows.append(
            {
                "service_key": field,
                "service_name": SERVICE_LABELS[field],
                "spend": value,
                "filled_guests": filled_guests,
                "share_of_total_revenue": value / total_revenue if total_revenue else 0.0,
            }
        )

    return sorted(rows, key=lambda item: item["spend"], reverse=True)


def build_top_guests(guests: list, limit: int = 25) -> list[dict]:
    top = sorted(guests, key=lambda guest: guest.total_revenue, reverse=True)[:limit]
    return [
        {
            "rank": index,
            "guest_name": guest.guest_name,
            "city": guest.city_normalized,
            "segment": guest.segment_label,
            "arrivals": guest.arrivals,
            "nights": guest.nights,
            "room_revenue": guest.room_revenue,
            "total_revenue": guest.total_revenue,
            "revenue_per_night": guest.revenue_per_night,
        }
        for index, guest in enumerate(top, start=1)
    ]


def build_data_quality(guests: list) -> dict:
    missing_city = [guest for guest in guests if not guest.city.strip()]
    missing_category = [guest for guest in guests if not guest.has_room_category]
    missing_name = [guest for guest in guests if not guest.guest_name.strip()]
    no_show_bookings = [
        guest for guest in guests if guest.nights == 0 and guest.total_revenue > 0
    ]
    room_revenue_gt_total = [
        guest for guest in guests if guest.room_revenue > guest.total_revenue
    ]
    unknown_segments = [guest for guest in guests if guest.segment_code == "unknown"]

    return {
        "guest_count": len(guests),
        "missing_city_count": len(missing_city),
        "missing_city_share": len(missing_city) / len(guests) if guests else 0.0,
        "missing_room_category_count": len(missing_category),
        "missing_room_category_share": (
            len(missing_category) / len(guests) if guests else 0.0
        ),
        "missing_guest_name_count": len(missing_name),
        "no_show_booking_count": len(no_show_bookings),
        "no_show_booking_revenue": sum(
            guest.total_revenue for guest in no_show_bookings
        ),
        "room_revenue_gt_total_count": len(room_revenue_gt_total),
        "unknown_segment_count": len(unknown_segments),
        "notes": [
            "Детализация по дополнительным услугам заполнена не для всех гостей.",
            "ФИО показываются только в детальных таблицах и топах.",
            "Нулевые ночи при наличии дохода считаются no-show бронированиями.",
        ],
    }


def write_csv(rows: list[dict], path: Path) -> None:
    if not rows:
        return

    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def write_json(data: dict | list, path: Path) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def run_profile(input_file: Path, output_dir: Path) -> dict:
    output_dir.mkdir(parents=True, exist_ok=True)
    csv_dir = output_dir / "csv"
    csv_dir.mkdir(parents=True, exist_ok=True)

    export_excel_to_csv(input_file=input_file, csv_dir=csv_dir)
    guests = parse_main_sheet(csv_dir)
    summary = build_summary(guests)

    clean_path = output_dir / "clean_guests.csv"
    profile_path = output_dir / "profile.json"
    summary_path = output_dir / "summary.json"
    data_quality_path = output_dir / "data_quality.json"

    clean_rows = [guest_to_dict(guest) for guest in guests]
    write_csv(clean_rows, clean_path)
    write_csv(
        aggregate_rows(guests, ["segment_code", "segment_label"]),
        output_dir / "segments.csv",
    )
    write_csv(aggregate_rows(guests, ["city_normalized"]), output_dir / "cities.csv")
    write_csv(
        aggregate_rows(guests, ["arrival_group"]),
        output_dir / "repeat_guests.csv",
    )
    write_csv(build_service_spend(guests), output_dir / "service_spend.csv")
    write_csv(build_top_guests(guests), output_dir / "top_guests.csv")

    data_quality = build_data_quality(guests)
    write_json(summary, profile_path)
    write_json(summary, summary_path)
    write_json(data_quality, data_quality_path)

    return {
        "summary": summary,
        "clean_path": str(clean_path),
        "profile_path": str(profile_path),
        "summary_path": str(summary_path),
        "data_quality_path": str(data_quality_path),
    }
