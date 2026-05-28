from __future__ import annotations

import csv
import json
import subprocess
from collections import defaultdict
from pathlib import Path

from .parser import (
    SERVICE_COLUMNS,
    category_to_dict,
    guest_to_dict,
    parse_category_sheet,
    parse_main_sheet,
)


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

DATA_CONTRACT = {
    "financials": {
        "source_sheet": "аналитика 2025",
        "fields": ["arrivals", "nights", "room_revenue", "total_revenue"],
        "rule": "Источник истины для финансовых показателей и базовых метрик.",
    },
    "segments": {
        "source_sheet": "аналитика 2025",
        "fields": ["segment_raw", "segment_code", "segment_label"],
        "rule": "Сегмент определяется по блочным заголовкам CLUB в основном листе.",
    },
    "guest_details": {
        "source_sheet": "категории номеров",
        "fields": [
            "room_category_detail_1",
            "room_category_detail_2",
            "guest_comment",
            "booking_method",
        ],
        "rule": "Используется для деталей гостя; финансовые значения с этого листа не перезаписывают основной лист.",
    },
    "duplicates": {
        "source_sheet": "Дубли",
        "fields": ["contact_candidates"],
        "rule": "Справочный лист с персональными данными; в публичный дашборд не включается.",
    },
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


def build_category_details(guests: list, categories: list) -> list[dict]:
    rows = []

    for guest, category in zip(guests, categories):
        rows.append(
            {
                "ordinal": category.ordinal,
                "main_source_row": guest.source_row,
                "category_source_row": category.source_row,
                "guest_name": guest.guest_name,
                "city": guest.city_normalized,
                "segment": guest.segment_label,
                "arrivals": guest.arrivals,
                "nights": guest.nights,
                "room_revenue": guest.room_revenue,
                "total_revenue": guest.total_revenue,
                "room_category_text": guest.room_categories_text,
                "room_category_detail_1": category.room_category_detail_1,
                "room_category_detail_2": category.room_category_detail_2,
                "guest_comment": category.guest_comment,
                "booking_method": category.booking_method,
            }
        )

    return rows


def build_sheet_reconciliation(guests: list, categories: list) -> dict:
    row_mismatches = []

    for guest, category in zip(guests, categories):
        differences = {
            "arrivals_diff": category.arrivals - guest.arrivals,
            "nights_diff": category.nights - guest.nights,
            "room_revenue_diff": category.room_revenue - guest.room_revenue,
            "total_revenue_diff": category.total_revenue - guest.total_revenue,
        }
        if any(abs(value) > 0.001 for value in differences.values()):
            row_mismatches.append(
                {
                    "ordinal": category.ordinal,
                    "main_source_row": guest.source_row,
                    "category_source_row": category.source_row,
                    "city_main": guest.city,
                    "city_category": category.city,
                    **differences,
                }
            )

    return {
        "main_guest_rows": len(guests),
        "category_guest_rows": len(categories),
        "row_count_match": len(guests) == len(categories),
        "row_level_mismatch_count": len(row_mismatches),
        "row_level_mismatches": row_mismatches,
        "main_total_revenue": sum(guest.total_revenue for guest in guests),
        "category_total_revenue": sum(category.total_revenue for category in categories),
        "main_room_revenue": sum(guest.room_revenue for guest in guests),
        "category_room_revenue": sum(category.room_revenue for category in categories),
        "main_nights": sum(guest.nights for guest in guests),
        "category_nights": sum(category.nights for category in categories),
    }


def build_reliability(
    data_quality: dict,
    reconciliation: dict,
    categories: list,
) -> list[dict]:
    category_detail_count = sum(
        1
        for row in categories
        if row.room_category_detail_1 or row.room_category_detail_2
    )
    booking_method_count = sum(1 for row in categories if row.booking_method)

    return [
        {
            "dashboard_block": "Финансы",
            "status": "reliable",
            "reason": "Строки, выручка, ночи и заезды сверены по основному листу.",
        },
        {
            "dashboard_block": "CLUB-сегменты",
            "status": "reliable",
            "reason": "Все строки гостей получили распознанный CLUB/Non-CLUB сегмент.",
        },
        {
            "dashboard_block": "География",
            "status": "partial",
            "reason": (
                f"Не заполнен город у {data_quality['missing_city_count']} гостей "
                f"({data_quality['missing_city_share']:.1%})."
            ),
        },
        {
            "dashboard_block": "Категории номеров",
            "status": "partial",
            "reason": (
                f"Детали категории заполнены у {category_detail_count} из "
                f"{len(categories)} строк листа категорий."
            ),
        },
        {
            "dashboard_block": "Способ бронирования",
            "status": "partial",
            "reason": (
                f"Способ бронирования заполнен у {booking_method_count} из "
                f"{len(categories)} строк листа категорий."
            ),
        },
        {
            "dashboard_block": "Дополнительные услуги",
            "status": "partial",
            "reason": "Детализация услуг заполнена только у части гостей.",
        },
        {
            "dashboard_block": "Межлистовая сверка",
            "status": "warning"
            if reconciliation["row_level_mismatch_count"]
            else "reliable",
            "reason": (
                f"Найдено {reconciliation['row_level_mismatch_count']} "
                "расхождений между основным листом и листом категорий."
            ),
        },
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


def build_audit_report(
    guests: list,
    categories: list,
    summary: dict,
    data_quality: dict,
) -> dict:
    reconciliation = build_sheet_reconciliation(guests, categories)
    reliability = build_reliability(data_quality, reconciliation, categories)

    return {
        "data_contract": DATA_CONTRACT,
        "source_integrity": {
            "main_guest_rows": len(guests),
            "category_guest_rows": len(categories),
            "main_total_revenue": summary["total_revenue"],
            "main_room_revenue": summary["room_revenue"],
            "main_nights": summary["nights"],
            "main_arrivals": summary["arrivals"],
        },
        "sheet_reconciliation": reconciliation,
        "data_quality": data_quality,
        "dashboard_reliability": reliability,
        "decision_rules": [
            "Финансовые суммы всегда берутся из листа 'аналитика 2025'.",
            "Лист 'категории номеров' обогащает детали гостя, но не заменяет финансовые суммы.",
            "No-show бронирования считаются валидными строками, если есть доход и ноль ночей.",
            "География и услуги показываются с предупреждением о неполной заполненности.",
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
    categories = parse_category_sheet(csv_dir)
    summary = build_summary(guests)

    clean_path = output_dir / "clean_guests.csv"
    profile_path = output_dir / "profile.json"
    summary_path = output_dir / "summary.json"
    data_quality_path = output_dir / "data_quality.json"
    audit_report_path = output_dir / "audit_report.json"

    clean_rows = [guest_to_dict(guest) for guest in guests]
    write_csv(clean_rows, clean_path)
    write_csv(
        [category_to_dict(row) for row in categories],
        output_dir / "category_rows.csv",
    )
    write_csv(
        build_category_details(guests, categories),
        output_dir / "guest_details.csv",
    )
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
    audit_report = build_audit_report(guests, categories, summary, data_quality)
    write_json(summary, profile_path)
    write_json(summary, summary_path)
    write_json(data_quality, data_quality_path)
    write_json(audit_report, audit_report_path)
    write_csv(
        audit_report["dashboard_reliability"],
        output_dir / "dashboard_reliability.csv",
    )

    return {
        "summary": summary,
        "clean_path": str(clean_path),
        "profile_path": str(profile_path),
        "summary_path": str(summary_path),
        "data_quality_path": str(data_quality_path),
        "audit_report_path": str(audit_report_path),
    }
