from __future__ import annotations

import csv
import re
from dataclasses import asdict, dataclass
from pathlib import Path


MAIN_SHEET = "аналитика 2025.csv"

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


@dataclass
class GuestRow:
    source_row: int
    guest_name: str
    city: str
    city_normalized: str
    segment: str
    arrivals: int
    months_text: str
    room_categories_text: str
    nights: float
    room_revenue: float
    total_revenue: float
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

        guests.append(
            GuestRow(
                source_row=source_row,
                guest_name=row[0].strip(),
                city=row[1].strip(),
                city_normalized=normalize_city(row[1]),
                segment=current_segment,
                arrivals=parse_int(row[2]),
                months_text=row[3].strip(),
                room_categories_text=row[4].strip(),
                nights=parse_money(row[5]),
                room_revenue=parse_money(row[6]),
                total_revenue=parse_money(row[7]),
                load_share_text=row[8].strip(),
                **service_values,
            )
        )

    return guests


def guest_to_dict(guest: GuestRow) -> dict:
    return asdict(guest)

