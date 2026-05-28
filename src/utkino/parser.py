from __future__ import annotations

import csv
import re
from dataclasses import asdict, dataclass
from pathlib import Path


MAIN_SHEET = "аналитика 2025.csv"
CATEGORY_SHEET = "категории номеров.csv"

SERVICE_COLUMNS = {
    "booking_room_sum": 9,
    "restaurant_spend": 10,
    "spa_spend": 11,
    "fishing_spend": 12,
    "laundry_spend": 13,
    "techpark_spend": 14,
    "horse_club_spend": 15,
    "cap_spend": 16,
    "transfer_spend": 17,
    "pets_spend": 18,
}

SEGMENT_RULES = [
    ("club_1_vip", "CLUB 1 VIP", "от 4 млн"),
    ("club_1_discount", "CLUB 1 discount", "действующей программе"),
    ("club_2", "CLUB 2", "CLUB 2"),
    ("club_3", "CLUB 3", "CLUB 3"),
    ("non_club", "Non-CLUB", "не попавшие"),
]


@dataclass
class GuestRow:
    source_row: int
    guest_name: str
    city: str
    city_normalized: str
    segment_raw: str
    segment_code: str
    segment_label: str
    arrivals: int
    arrival_group: str
    is_repeat_guest: bool
    months_text: str
    room_categories_text: str
    has_room_category: bool
    nights: float
    room_revenue: float
    total_revenue: float
    extra_revenue: float
    revenue_per_night: float
    revenue_per_arrival: float
    room_revenue_share: float
    load_share_text: str
    booking_room_sum: float
    restaurant_spend: float
    spa_spend: float
    fishing_spend: float
    laundry_spend: float
    techpark_spend: float
    horse_club_spend: float
    cap_spend: float
    transfer_spend: float
    pets_spend: float


@dataclass
class CategoryRow:
    ordinal: int
    source_row: int
    city: str
    arrivals: int
    nights: float
    room_revenue: float
    total_revenue: float
    load_share_text: str
    room_category_detail_1: str
    room_category_detail_2: str
    guest_comment: str
    booking_method: str


def parse_money(value: str) -> float:
    cleaned = (value or "").strip().replace(" ", "").replace("%", "").replace(",", "")
    if not cleaned or cleaned == "-":
        return 0.0
    return float(cleaned)


def parse_int(value: str) -> int:
    cleaned = (value or "").strip().replace(",", ".")
    if not cleaned:
        return 0
    return int(float(cleaned))


def normalize_city(value: str) -> str:
    city = (value or "").strip().lower().replace("ё", "е")
    city = re.sub(r"^(г\.?|город)\s*", "", city)
    city = re.sub(r"\s+", " ", city).strip()

    aliases = {
        "рнд": "Ростов-на-Дону",
        "ростов": "Ростов-на-Дону",
        "ростов на дону": "Ростов-на-Дону",
        "ростов-на дону": "Ростов-на-Дону",
        "ростов-на-дону": "Ростов-на-Дону",
        "москва": "Москва",
    }
    if not city:
        return "(город не указан)"
    return aliases.get(city, city.title())


def normalize_segment(value: str) -> tuple[str, str]:
    segment = value or ""
    for code, label, marker in SEGMENT_RULES:
        if marker.lower() in segment.lower():
            return code, label
    return "unknown", "Unknown"


def arrival_group(arrivals: int) -> str:
    if arrivals <= 1:
        return "1"
    if arrivals == 2:
        return "2"
    return "3+"


def looks_like_segment(row: list[str]) -> bool:
    first = row[0].strip() if row else ""
    second = row[1].strip() if len(row) > 1 else ""
    third = row[2].strip() if len(row) > 2 else ""
    return bool(first and not second and not third and first != "ФИО гостя")


def looks_like_guest(row: list[str]) -> bool:
    if len(row) < 8:
        return False
    if row[0].strip() == "ФИО гостя":
        return False
    return bool(row[2].strip() and row[7].strip())


def parse_main_sheet(csv_dir: Path) -> list[GuestRow]:
    path = csv_dir / MAIN_SHEET
    with path.open(encoding="cp1251", newline="") as handle:
        rows = list(csv.reader(handle))

    guests: list[GuestRow] = []
    current_segment = ""

    for source_row, row in enumerate(rows, start=1):
        row = row + [""] * (19 - len(row))

        if looks_like_segment(row):
            current_segment = row[0].strip()
            continue

        if not looks_like_guest(row):
            continue

        service_values = {
            field: parse_money(row[index])
            for field, index in SERVICE_COLUMNS.items()
        }
        arrivals = parse_int(row[2])
        nights = parse_money(row[5])
        room_revenue = parse_money(row[6])
        total_revenue = parse_money(row[7])
        segment_code, segment_label = normalize_segment(current_segment)

        guests.append(
            GuestRow(
                source_row=source_row,
                guest_name=row[0].strip(),
                city=row[1].strip(),
                city_normalized=normalize_city(row[1]),
                segment_raw=current_segment,
                segment_code=segment_code,
                segment_label=segment_label,
                arrivals=arrivals,
                arrival_group=arrival_group(arrivals),
                is_repeat_guest=arrivals > 1,
                months_text=row[3].strip(),
                room_categories_text=row[4].strip(),
                has_room_category=bool(row[4].strip()),
                nights=nights,
                room_revenue=room_revenue,
                total_revenue=total_revenue,
                extra_revenue=total_revenue - room_revenue,
                revenue_per_night=total_revenue / nights if nights else 0.0,
                revenue_per_arrival=total_revenue / arrivals if arrivals else 0.0,
                room_revenue_share=room_revenue / total_revenue if total_revenue else 0.0,
                load_share_text=row[8].strip(),
                **service_values,
            )
        )

    return guests


def parse_category_sheet(csv_dir: Path) -> list[CategoryRow]:
    path = csv_dir / CATEGORY_SHEET
    with path.open(encoding="cp1251", newline="") as handle:
        rows = list(csv.reader(handle))

    category_rows: list[CategoryRow] = []

    for source_row, row in enumerate(rows, start=1):
        row = row + [""] * (11 - len(row))

        if len(row) < 6 or row[0].strip() == "ФИО гостя":
            continue

        if not row[2].strip() or not row[5].strip():
            continue

        category_rows.append(
            CategoryRow(
                ordinal=len(category_rows) + 1,
                source_row=source_row,
                city=row[1].strip(),
                arrivals=parse_int(row[2]),
                nights=parse_money(row[3]),
                room_revenue=parse_money(row[4]),
                total_revenue=parse_money(row[5]),
                load_share_text=row[6].strip(),
                room_category_detail_1=row[7].strip(),
                room_category_detail_2=row[8].strip(),
                guest_comment=row[9].strip(),
                booking_method=row[10].strip(),
            )
        )

    return category_rows


def guest_to_dict(guest: GuestRow) -> dict:
    return asdict(guest)


def category_to_dict(category: CategoryRow) -> dict:
    return asdict(category)
