from __future__ import annotations

import csv
import html
import json
from pathlib import Path


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def read_csv(path: Path) -> list[dict]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def money(value: float | str) -> str:
    return f"{float(value):,.0f}".replace(",", " ") + " ₽"


def number(value: float | str) -> str:
    raw = float(value)
    if raw.is_integer():
        return f"{int(raw):,}".replace(",", " ")
    return f"{raw:,.1f}".replace(",", " ")


def percent(value: float | str) -> str:
    return f"{float(value) * 100:.1f}%"


def esc(value: object) -> str:
    return html.escape(str(value if value is not None else ""))


def status_label(status: str) -> str:
    labels = {
        "reliable": "надежно",
        "partial": "частично",
        "warning": "внимание",
    }
    return labels.get(status, status)


def bar_chart(
    rows: list[dict],
    label_key: str,
    value_key: str,
    value_formatter,
    limit: int = 8,
) -> str:
    chart_rows = rows[:limit]
    if not chart_rows:
        return '<p class="empty">Нет данных</p>'

    max_value = max(float(row[value_key]) for row in chart_rows) or 1.0
    items = []
    for row in chart_rows:
        value = float(row[value_key])
        width = max(value / max_value * 100, 1.5)
        items.append(
            f"""
            <div class="bar-row">
              <div class="bar-label">{esc(row[label_key])}</div>
              <div class="bar-track">
                <div class="bar-fill" style="width:{width:.2f}%"></div>
              </div>
              <div class="bar-value">{esc(value_formatter(value))}</div>
            </div>
            """
        )
    return "\n".join(items)


def donut_chart(
    rows: list[dict],
    label_key: str,
    value_key: str,
    value_formatter,
    limit: int = 6,
) -> str:
    chart_rows = rows[:limit]
    total = sum(float(row[value_key]) for row in chart_rows)
    if not chart_rows or not total:
        return '<p class="empty">Нет данных</p>'

    colors = ["#0f766e", "#2563eb", "#b45309", "#7c3aed", "#dc2626", "#64748b"]
    radius = 70
    circumference = 2 * 3.141592653589793 * radius
    offset = 0.0
    circles = []
    legend = []

    for index, row in enumerate(chart_rows):
        value = float(row[value_key])
        share = value / total
        dash = share * circumference
        color = colors[index % len(colors)]
        circles.append(
            f"""
            <circle r="{radius}" cx="100" cy="100"
              fill="transparent"
              stroke="{color}"
              stroke-width="28"
              stroke-dasharray="{dash:.2f} {circumference - dash:.2f}"
              stroke-dashoffset="{-offset:.2f}"
              transform="rotate(-90 100 100)" />
            """
        )
        offset += dash
        legend.append(
            f"""
            <div class="legend-row">
              <span class="legend-swatch" style="background:{color}"></span>
              <span>{esc(row[label_key])}</span>
              <strong>{esc(value_formatter(value))}</strong>
            </div>
            """
        )

    return f"""
    <div class="donut-layout">
      <svg class="donut" viewBox="0 0 200 200" role="img">
        <circle r="{radius}" cx="100" cy="100" fill="transparent"
          stroke="#e8edf4" stroke-width="28" />
        {''.join(circles)}
        <text x="100" y="95" text-anchor="middle" class="donut-total">
          {esc(value_formatter(total))}
        </text>
        <text x="100" y="116" text-anchor="middle" class="donut-caption">итого</text>
      </svg>
      <div class="legend">{''.join(legend)}</div>
    </div>
    """


CITY_COORDS = {
    "Ростов-на-Дону": (47.2357, 39.7015),
    "Москва": (55.7558, 37.6173),
    "Батайск": (47.1398, 39.7518),
    "Краснодар": (45.0355, 38.9753),
    "Шахты": (47.7085, 40.2159),
    "Новочеркасск": (47.4221, 40.0938),
    "Волгодонск": (47.5165, 42.1985),
    "Аксай": (47.2676, 39.8758),
    "Видное": (55.5516, 37.7065),
    "Таганрог": (47.2362, 38.8969),
    "Ставрополь": (45.0448, 41.9690),
    "Сочи": (43.5855, 39.7231),
    "Воронеж": (51.6608, 39.2003),
    "Санкт-Петербург": (59.9311, 30.3609),
    "Алушта": (44.6764, 34.4100),
}


def city_bubble_map(cities: list[dict], limit: int = 14) -> str:
    mapped = [
        row
        for row in cities
        if row["city_normalized"] in CITY_COORDS
        and row["city_normalized"] != "(город не указан)"
    ][:limit]
    if not mapped:
        return '<p class="empty">Нет координат для городов</p>'

    values = [float(row["total_revenue"]) for row in mapped]
    max_value = max(values) or 1.0
    lats = [CITY_COORDS[row["city_normalized"]][0] for row in mapped]
    lons = [CITY_COORDS[row["city_normalized"]][1] for row in mapped]
    min_lat, max_lat = min(lats), max(lats)
    min_lon, max_lon = min(lons), max(lons)

    def project(lat: float, lon: float) -> tuple[float, float]:
        x = 50 + (lon - min_lon) / max(max_lon - min_lon, 0.1) * 620
        y = 310 - (lat - min_lat) / max(max_lat - min_lat, 0.1) * 250
        return x, y

    bubbles = []
    labels = []
    for row in mapped:
        city = row["city_normalized"]
        lat, lon = CITY_COORDS[city]
        x, y = project(lat, lon)
        value = float(row["total_revenue"])
        radius = 8 + (value / max_value) ** 0.5 * 28
        bubbles.append(
            f"""
            <circle cx="{x:.1f}" cy="{y:.1f}" r="{radius:.1f}"
              class="map-bubble">
              <title>{esc(city)}: {esc(money(value))}</title>
            </circle>
            """
        )
        labels.append(
            f"""
            <text x="{x + radius + 5:.1f}" y="{y + 4:.1f}" class="map-label">
              {esc(city)}
            </text>
            """
        )

    return f"""
    <svg class="map-svg" viewBox="0 0 720 360" role="img"
      aria-label="Карта городов по доходу">
      <rect x="1" y="1" width="718" height="358" rx="8" class="map-bg" />
      <path d="M60 300 C180 230 250 260 330 190 C430 105 540 95 660 70"
        class="map-route" />
      {''.join(bubbles)}
      {''.join(labels)}
    </svg>
    """


def metric_scatter(rows: list[dict], limit: int = 12) -> str:
    points = rows[:limit]
    if not points:
        return '<p class="empty">Нет данных</p>'

    revenues = [float(row["total_revenue"]) for row in points]
    guests = [float(row["guests"]) for row in points]
    max_revenue = max(revenues) or 1.0
    max_guests = max(guests) or 1.0
    circles = []

    for row in points:
        x = 55 + float(row["guests"]) / max_guests * 610
        y = 295 - float(row["total_revenue"]) / max_revenue * 245
        radius = 7 + (float(row["nights"]) / max(float(r["nights"]) for r in points)) * 16
        circles.append(
            f"""
            <g>
              <circle cx="{x:.1f}" cy="{y:.1f}" r="{radius:.1f}"
                class="scatter-dot">
                <title>{esc(row['city_normalized'])}: {esc(money(row['total_revenue']))}</title>
              </circle>
              <text x="{x + radius + 4:.1f}" y="{y + 4:.1f}" class="map-label">
                {esc(row['city_normalized'])}
              </text>
            </g>
            """
        )

    return f"""
    <svg class="scatter-svg" viewBox="0 0 720 340" role="img"
      aria-label="Города: гости и доход">
      <line x1="55" y1="300" x2="680" y2="300" class="axis" />
      <line x1="55" y1="300" x2="55" y2="40" class="axis" />
      <text x="360" y="330" class="axis-label">гостей</text>
      <text x="14" y="44" class="axis-label">доход</text>
      {''.join(circles)}
    </svg>
    """


def kpi_card(label: str, value: str, hint: str = "") -> str:
    return f"""
    <div class="kpi">
      <div class="kpi-label">{esc(label)}</div>
      <div class="kpi-value">{esc(value)}</div>
      <div class="kpi-hint">{esc(hint)}</div>
    </div>
    """


def table(headers: list[tuple[str, str]], rows: list[dict], limit: int | None = None) -> str:
    selected_rows = rows if limit is None else rows[:limit]
    head = "".join(f"<th>{esc(title)}</th>" for _, title in headers)
    body_rows = []
    for row in selected_rows:
        cells = "".join(f"<td>{esc(row.get(key, ''))}</td>" for key, _ in headers)
        body_rows.append(f"<tr>{cells}</tr>")
    body = "\n".join(body_rows) or (
        f'<tr><td colspan="{len(headers)}" class="empty">Нет данных</td></tr>'
    )
    return f"""
    <div class="table-wrap">
      <table>
        <thead><tr>{head}</tr></thead>
        <tbody>{body}</tbody>
      </table>
    </div>
    """


def build_dashboard(profile_dir: Path, output_file: Path) -> Path:
    summary = read_json(profile_dir / "summary.json")
    data_quality = read_json(profile_dir / "data_quality.json")
    audit = read_json(profile_dir / "audit_report.json")
    segments = read_csv(profile_dir / "segments.csv")
    cities = read_csv(profile_dir / "cities.csv")
    repeat = read_csv(profile_dir / "repeat_guests.csv")
    services = read_csv(profile_dir / "service_spend.csv")
    top_guests = read_csv(profile_dir / "top_guests.csv")
    reliability = read_csv(profile_dir / "dashboard_reliability.csv")

    repeat_labels = {"1": "1 заезд", "2": "2 заезда", "3+": "3+ заездов"}
    for row in repeat:
        row["arrival_group_label"] = repeat_labels.get(
            row["arrival_group"],
            row["arrival_group"],
        )

    for row in top_guests:
        row["total_revenue"] = money(row["total_revenue"])
        row["room_revenue"] = money(row["room_revenue"])
        row["revenue_per_night"] = money(row["revenue_per_night"])
        row["nights"] = number(row["nights"])

    for row in reliability:
        row["status"] = status_label(row["status"])

    reconciliation = audit["sheet_reconciliation"]
    segment_table_rows = [
        {
            **row,
            "total_revenue": money(row["total_revenue"]),
            "average_revenue_per_guest": money(row["average_revenue_per_guest"]),
            "repeat_guest_share": percent(row["repeat_guest_share"]),
        }
        for row in segments
    ]
    city_table_rows = [
        {
            **row,
            "total_revenue": money(row["total_revenue"]),
            "average_revenue_per_guest": money(row["average_revenue_per_guest"]),
        }
        for row in cities
    ]
    repeat_table_rows = [
        {
            **row,
            "total_revenue": money(row["total_revenue"]),
            "average_revenue_per_guest": money(row["average_revenue_per_guest"]),
        }
        for row in repeat
    ]

    html_text = f"""<!doctype html>
<html lang="ru">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Utkino Analytics 2025</title>
  <style>
    :root {{
      --bg: #f6f7f9;
      --surface: #ffffff;
      --line: #d9dee7;
      --text: #17202e;
      --muted: #697386;
      --accent: #0f766e;
      --accent-2: #2563eb;
      --warn: #b45309;
      --bad: #b91c1c;
      --good: #047857;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      background: var(--bg);
      color: var(--text);
      font-family: "Segoe UI", Arial, sans-serif;
      line-height: 1.45;
    }}
    header {{
      background: #17202e;
      color: #fff;
      padding: 28px 32px 24px;
    }}
    header h1 {{
      margin: 0 0 8px;
      font-size: 28px;
      font-weight: 650;
      letter-spacing: 0;
    }}
    header p {{ margin: 0; color: #c9d2df; }}
    main {{ padding: 24px 32px 40px; max-width: 1440px; margin: 0 auto; }}
    .tabs {{
      display: flex;
      gap: 6px;
      flex-wrap: wrap;
      margin-bottom: 18px;
    }}
    .tab-button {{
      border: 1px solid var(--line);
      background: var(--surface);
      color: var(--text);
      border-radius: 6px;
      padding: 9px 13px;
      cursor: pointer;
      font-size: 14px;
    }}
    .tab-button.active {{
      background: var(--accent);
      border-color: var(--accent);
      color: #fff;
    }}
    .section {{ display: none; }}
    .section.active {{ display: block; }}
    .grid {{
      display: grid;
      grid-template-columns: repeat(12, minmax(0, 1fr));
      gap: 16px;
      align-items: start;
    }}
    .panel {{
      background: var(--surface);
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 18px;
    }}
    .span-3 {{ grid-column: span 3; }}
    .span-4 {{ grid-column: span 4; }}
    .span-6 {{ grid-column: span 6; }}
    .span-8 {{ grid-column: span 8; }}
    .span-12 {{ grid-column: span 12; }}
    .panel h2, .panel h3 {{
      margin: 0 0 14px;
      font-size: 17px;
      font-weight: 650;
    }}
    .kpi {{
      min-height: 116px;
      background: var(--surface);
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 16px;
    }}
    .kpi-label {{ color: var(--muted); font-size: 13px; }}
    .kpi-value {{ font-size: 24px; font-weight: 700; margin-top: 8px; }}
    .kpi-hint {{ color: var(--muted); font-size: 12px; margin-top: 8px; }}
    .bar-row {{
      display: grid;
      grid-template-columns: minmax(140px, 230px) 1fr minmax(90px, 140px);
      gap: 10px;
      align-items: center;
      margin: 10px 0;
      font-size: 13px;
    }}
    .bar-label {{
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }}
    .bar-track {{
      height: 12px;
      background: #e8edf4;
      border-radius: 999px;
      overflow: hidden;
    }}
    .bar-fill {{
      height: 100%;
      background: linear-gradient(90deg, var(--accent), var(--accent-2));
    }}
    .bar-value {{ text-align: right; color: var(--muted); }}
    .donut-layout {{
      display: grid;
      grid-template-columns: minmax(170px, 220px) 1fr;
      gap: 18px;
      align-items: center;
    }}
    .donut {{ width: 100%; max-width: 220px; }}
    .donut-total {{
      font-size: 18px;
      font-weight: 700;
      fill: var(--text);
    }}
    .donut-caption {{ font-size: 11px; fill: var(--muted); }}
    .legend {{ display: grid; gap: 8px; font-size: 13px; }}
    .legend-row {{
      display: grid;
      grid-template-columns: 12px 1fr auto;
      gap: 8px;
      align-items: center;
    }}
    .legend-swatch {{
      width: 12px;
      height: 12px;
      border-radius: 3px;
    }}
    .map-svg, .scatter-svg {{
      display: block;
      width: 100%;
      height: auto;
      min-height: 280px;
    }}
    .map-bg {{ fill: #eef4f1; stroke: var(--line); }}
    .map-route {{
      fill: none;
      stroke: #b8c5d6;
      stroke-width: 22;
      stroke-linecap: round;
      opacity: 0.55;
    }}
    .map-bubble {{
      fill: rgba(15, 118, 110, 0.72);
      stroke: #ffffff;
      stroke-width: 2;
    }}
    .map-label, .axis-label {{
      font-size: 11px;
      fill: var(--muted);
    }}
    .scatter-dot {{
      fill: rgba(37, 99, 235, 0.68);
      stroke: #ffffff;
      stroke-width: 2;
    }}
    .axis {{
      stroke: #a9b4c4;
      stroke-width: 1;
    }}
    .table-wrap {{ overflow-x: auto; }}
    table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
    th, td {{
      border-bottom: 1px solid var(--line);
      padding: 9px 8px;
      text-align: left;
      vertical-align: top;
    }}
    th {{ color: var(--muted); font-weight: 650; background: #f8fafc; }}
    .notice {{
      border-left: 4px solid var(--warn);
      background: #fff7ed;
      padding: 12px 14px;
      border-radius: 6px;
      color: #7c2d12;
      margin-bottom: 16px;
    }}
    .status-pill {{
      display: inline-block;
      border: 1px solid var(--line);
      border-radius: 999px;
      padding: 3px 8px;
      font-size: 12px;
      color: var(--muted);
      background: #fff;
    }}
    .empty {{ color: var(--muted); }}
    .search {{
      width: 100%;
      max-width: 360px;
      border: 1px solid var(--line);
      border-radius: 6px;
      padding: 9px 10px;
      margin-bottom: 12px;
      font-size: 14px;
    }}
    @media (max-width: 980px) {{
      main {{ padding: 18px; }}
      .span-3, .span-4, .span-6, .span-8 {{ grid-column: span 12; }}
      .donut-layout {{ grid-template-columns: 1fr; }}
      .bar-row {{ grid-template-columns: 1fr; gap: 5px; }}
      .bar-value {{ text-align: left; }}
    }}
  </style>
</head>
<body>
  <header>
    <h1>Utkino Analytics 2025</h1>
    <p>Аналитический отчет по гостям, выручке, сегментам и качеству данных</p>
  </header>
  <main>
    <nav class="tabs" aria-label="Разделы отчета">
      <button class="tab-button active" data-tab="overview">Обзор</button>
      <button class="tab-button" data-tab="segments">CLUB</button>
      <button class="tab-button" data-tab="geo">География</button>
      <button class="tab-button" data-tab="loyalty">Лояльность</button>
      <button class="tab-button" data-tab="services">Услуги</button>
      <button class="tab-button" data-tab="details">Топы</button>
      <button class="tab-button" data-tab="audit">Audit</button>
    </nav>

    <section id="overview" class="section active">
      <div class="grid">
        <div class="span-3">{kpi_card("Общий доход", money(summary["total_revenue"]), "Источник: аналитика 2025")}</div>
        <div class="span-3">{kpi_card("Гостей", number(summary["guest_count"]), f"{number(summary['arrivals'])} заездов")}</div>
        <div class="span-3">{kpi_card("Ночей", number(summary["nights"]), f"{money(summary['average_revenue_per_night'])} на ночь")}</div>
        <div class="span-3">{kpi_card("Повторные гости", percent(summary["repeat_guest_share"]), f"{percent(summary['repeat_revenue_share'])} выручки")}</div>
        <div class="panel span-6">
          <h2>Структура выручки по сегментам</h2>
          {donut_chart(segments, "segment_label", "total_revenue", money, 6)}
        </div>
        <div class="panel span-6">
          <h2>Топ городов по доходу</h2>
          {bar_chart(cities, "city_normalized", "total_revenue", money, 8)}
        </div>
      </div>
    </section>

    <section id="segments" class="section">
      <div class="grid">
        <div class="panel span-8">
          <h2>Средний доход на гостя</h2>
          {bar_chart(segments, "segment_label", "average_revenue_per_guest", money, 6)}
        </div>
        <div class="panel span-4">
          <h2>Статус блока</h2>
          <p><span class="status-pill">надежно</span></p>
          <p>Все строки гостей получили распознанный CLUB/Non-CLUB сегмент.</p>
        </div>
        <div class="panel span-12">
          {table([
              ("segment_label", "Сегмент"),
              ("guests", "Гостей"),
              ("arrivals", "Заездов"),
              ("nights", "Ночей"),
              ("total_revenue", "Общий доход"),
              ("average_revenue_per_guest", "Доход на гостя"),
              ("repeat_guest_share", "Доля повторных"),
          ], segment_table_rows)}
        </div>
      </div>
    </section>

    <section id="geo" class="section">
      <div class="notice">У {data_quality["missing_city_count"]} гостей не заполнен город. География рассчитана по доступным значениям, а неизвестный город показан отдельно.</div>
      <div class="grid">
        <div class="panel span-8">
          <h2>Города на карте</h2>
          {city_bubble_map(cities, 14)}
        </div>
        <div class="panel span-4">
          <h2>Качество географии</h2>
          {kpi_card("Без города", percent(data_quality["missing_city_share"]), f"{data_quality['missing_city_count']} гостей")}
          <p class="empty">Карта использует встроенный справочник координат для основных городов.</p>
        </div>
        <div class="panel span-6">
          <h2>Города по доходу</h2>
          {bar_chart(cities, "city_normalized", "total_revenue", money, 12)}
        </div>
        <div class="panel span-6">
          <h2>Гости и доход по городам</h2>
          {metric_scatter([row for row in cities if row["city_normalized"] != "(город не указан)"], 12)}
        </div>
        <div class="panel span-12">
          {table([
              ("city_normalized", "Город"),
              ("guests", "Гостей"),
              ("arrivals", "Заездов"),
              ("nights", "Ночей"),
              ("total_revenue", "Доход"),
              ("average_revenue_per_guest", "Доход на гостя"),
          ], city_table_rows, 25)}
        </div>
      </div>
    </section>

    <section id="loyalty" class="section">
      <div class="grid">
        <div class="panel span-6">
          <h2>Выручка по числу заездов</h2>
          {donut_chart(repeat, "arrival_group_label", "total_revenue", money, 3)}
        </div>
        <div class="panel span-6">
          <h2>No-show бронирования</h2>
          {kpi_card("No-show", number(data_quality["no_show_booking_count"]), money(data_quality["no_show_booking_revenue"]))}
        </div>
        <div class="panel span-12">
          {table([
              ("arrival_group_label", "Группа"),
              ("guests", "Гостей"),
              ("arrivals", "Заездов"),
              ("nights", "Ночей"),
              ("total_revenue", "Доход"),
              ("average_revenue_per_guest", "Доход на гостя"),
          ], repeat_table_rows)}
        </div>
      </div>
    </section>

    <section id="services" class="section">
      <div class="notice">Детализация дополнительных услуг заполнена частично, поэтому блок показывает только явно заполненные суммы.</div>
      <div class="grid">
        <div class="panel span-6">
          <h2>Структура дополнительных услуг</h2>
          {donut_chart(services, "service_name", "spend", money, 8)}
        </div>
        <div class="panel span-6">
          <h2>Дополнительные услуги</h2>
          {bar_chart(services, "service_name", "spend", money, 10)}
        </div>
        <div class="panel span-12">
          <h2>Покрытие данных</h2>
          {table([
              ("service_name", "Услуга"),
              ("filled_guests", "Строк"),
          ], services)}
        </div>
      </div>
    </section>

    <section id="details" class="section">
      <div class="panel">
        <h2>Топ гостей по доходу</h2>
        <input class="search" id="guestSearch" type="search" placeholder="Поиск по городу или сегменту">
        {table([
            ("rank", "#"),
            ("guest_name", "ФИО"),
            ("city", "Город"),
            ("segment", "Сегмент"),
            ("arrivals", "Заездов"),
            ("nights", "Ночей"),
            ("room_revenue", "Комнаты"),
            ("total_revenue", "Общий доход"),
            ("revenue_per_night", "На ночь"),
        ], top_guests)}
      </div>
    </section>

    <section id="audit" class="section">
      <div class="grid">
        <div class="panel span-6">
          <h2>Надежность блоков</h2>
          {table([
              ("dashboard_block", "Блок"),
              ("status", "Статус"),
              ("reason", "Комментарий"),
          ], reliability)}
        </div>
        <div class="panel span-6">
          <h2>Межлистовая сверка</h2>
          {kpi_card("Расхождений", number(reconciliation["row_level_mismatch_count"]), "Основной лист остается источником финансов")}
          <p>Сумма основного листа: <strong>{money(reconciliation["main_total_revenue"])}</strong></p>
          <p>Сумма листа категорий: <strong>{money(reconciliation["category_total_revenue"])}</strong></p>
        </div>
      </div>
    </section>
  </main>
  <script>
    const buttons = document.querySelectorAll(".tab-button");
    const sections = document.querySelectorAll(".section");
    buttons.forEach((button) => {{
      button.addEventListener("click", () => {{
        buttons.forEach((item) => item.classList.remove("active"));
        sections.forEach((item) => item.classList.remove("active"));
        button.classList.add("active");
        document.getElementById(button.dataset.tab).classList.add("active");
      }});
    }});

    const search = document.getElementById("guestSearch");
    if (search) {{
      search.addEventListener("input", () => {{
        const query = search.value.toLowerCase();
        const rows = search.closest(".panel").querySelectorAll("tbody tr");
        rows.forEach((row) => {{
          row.style.display = row.innerText.toLowerCase().includes(query) ? "" : "none";
        }});
      }});
    }}
  </script>
</body>
</html>
"""

    output_file.parent.mkdir(parents=True, exist_ok=True)
    output_file.write_text(html_text, encoding="utf-8")
    return output_file
