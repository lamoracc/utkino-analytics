from __future__ import annotations

import csv
import html
import json
from datetime import datetime
from pathlib import Path


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def read_csv(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def money(value: float | str) -> str:
    return f"{as_float_value(value):,.0f}".replace(",", " ") + " ₽"


def number(value: float | str) -> str:
    raw = as_float_value(value)
    if raw.is_integer():
        return f"{int(raw):,}".replace(",", " ")
    return f"{raw:,.1f}".replace(",", " ")


def percent(value: float | str) -> str:
    return f"{as_float_value(value) * 100:.1f}%"


def esc(value: object) -> str:
    return html.escape(str(value if value is not None else ""))


def status_label(status: str) -> str:
    labels = {
        "reliable": "надежно",
        "partial": "частично",
        "warning": "внимание",
    }
    return labels.get(status, status)


def as_float_value(value: object) -> float:
    try:
        return float(str(value or "0").replace(" ", "").replace("\u00a0", ""))
    except ValueError:
        return 0.0


def status_class(status: str) -> str:
    classes = {
        "reliable": "status-good",
        "partial": "status-warning",
        "warning": "status-bad",
    }
    return classes.get(status, "status-neutral")


def format_report_datetime(value: str) -> str:
    if not value:
        return ""
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return value
    return parsed.strftime("%d.%m.%Y %H:%M:%S")


def as_float(row: dict, key: str) -> float:
    try:
        return float(row.get(key, 0) or 0)
    except ValueError:
        return 0.0


def as_int(row: dict, key: str) -> int:
    return int(as_float(row, key))


def guest_display(row: dict, fallback: str) -> str:
    return row.get("guest_name") or fallback


def guest_modal_id(prefix: str, index: int) -> str:
    return f"{prefix}-{index}"


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

    max_value = max(as_float(row, value_key) for row in chart_rows) or 1.0
    items = []
    for row in chart_rows:
        value = as_float(row, value_key)
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


def kpi_card(label: str, value: str, hint: str = "", modal_id: str = "") -> str:
    modal_attr = f' data-modal-open="{esc(modal_id)}"' if modal_id else ""
    clickable_class = " clickable" if modal_id else ""
    action = '<div class="kpi-action">Подробнее</div>' if modal_id else ""
    return f"""
    <div class="kpi{clickable_class}"{modal_attr}>
      <div class="kpi-label">{esc(label)}</div>
      <div class="kpi-value">{esc(value)}</div>
      <div class="kpi-hint">{esc(hint)}</div>
      {action}
    </div>
    """


def table(
    headers: list[tuple[str, str]],
    rows: list[dict],
    limit: int | None = None,
    row_attrs=None,
    table_class: str = "",
) -> str:
    selected_rows = rows if limit is None else rows[:limit]
    class_attr = f' class="{esc(table_class)}"' if table_class else ""
    head = "".join(f'<th data-sort-key="{esc(key)}">{esc(title)}</th>' for key, title in headers)
    body_rows = []
    for index, row in enumerate(selected_rows):
        attrs = f" {row_attrs(row, index)}" if row_attrs else ""
        cells = "".join(f"<td>{esc(row.get(key, ''))}</td>" for key, _ in headers)
        body_rows.append(f"<tr{attrs}>{cells}</tr>")
    body = "\n".join(body_rows) or (
        f'<tr><td colspan="{len(headers)}" class="empty">Нет данных</td></tr>'
    )
    return f"""
    <div class="table-wrap">
      <table{class_attr}>
        <thead><tr>{head}</tr></thead>
        <tbody>{body}</tbody>
      </table>
    </div>
    """


def modal(modal_id: str, title: str, body: str) -> str:
    modal_class = "modal modal-scroll" if modal_id == "revenue-modal" else "modal"
    return f"""
    <div class="modal-backdrop" id="{esc(modal_id)}" aria-hidden="true">
      <div class="{modal_class}" role="dialog" aria-modal="true" aria-labelledby="{esc(modal_id)}-title">
        <button class="modal-close" type="button" data-modal-close aria-label="Закрыть">×</button>
        <h2 id="{esc(modal_id)}-title">{esc(title)}</h2>
        {body}
      </div>
    </div>
    """


def build_dashboard(
    profile_dir: Path,
    output_file: Path,
    metadata: dict | None = None,
) -> Path:
    metadata = metadata or {}
    summary = read_json(profile_dir / "summary.json")
    data_quality = read_json(profile_dir / "data_quality.json")
    audit = read_json(profile_dir / "audit_report.json")
    segments = read_csv(profile_dir / "segments.csv")
    cities = read_csv(profile_dir / "cities.csv")
    repeat = read_csv(profile_dir / "repeat_guests.csv")
    services = read_csv(profile_dir / "service_spend.csv")
    top_guests_raw = read_csv(profile_dir / "top_guests.csv")
    top_guests = [dict(row) for row in top_guests_raw]
    clean_guests = read_csv(profile_dir / "clean_guests.csv")
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

    reliability_rows = []
    for row in reliability:
        status = row.get("status", "")
        reliability_rows.append(
            {
                **row,
                "status": status_label(status),
                "status_code": status,
            }
        )

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
    metadata_rows = [
        ("Файл", metadata.get("input_file_name", "Data/Utkino.xls")),
        ("Сформировано", format_report_datetime(metadata.get("generated_at", ""))),
        (
            "Excel изменен",
            format_report_datetime(metadata.get("input_file_modified_at", "")),
        ),
    ]
    metadata_html = "".join(
        f"<span><strong>{esc(label)}:</strong> {esc(value)}</span>"
        for label, value in metadata_rows
        if value
    )
    top_revenue_guests = sorted(
        clean_guests,
        key=lambda row: as_float(row, "total_revenue"),
        reverse=True,
    )[:5]
    top_repeat_guests = sorted(
        [row for row in clean_guests if as_int(row, "arrivals") > 1],
        key=lambda row: (as_int(row, "arrivals"), as_float(row, "total_revenue")),
        reverse=True,
    )[:15]
    no_show_guests = sorted(
        [
            row
            for row in clean_guests
            if as_int(row, "arrivals") == 0
        ],
        key=lambda row: as_float(row, "total_revenue"),
        reverse=True,
    )
    no_show_table_rows = [
        {
            "guest_name": guest_display(row, f"Гость #{index}"),
            "city": row.get("city_normalized", ""),
            "segment": row.get("segment_label", ""),
            "arrivals": row.get("arrivals", ""),
            "nights": number(row.get("nights", 0)),
            "total_revenue": money(row.get("total_revenue", 0)),
        }
        for index, row in enumerate(no_show_guests[:25], start=1)
    ]
    repeat_guest_table_rows = [
        {
            "guest_name": guest_display(row, f"Гость #{index}"),
            "city": row.get("city_normalized", ""),
            "segment": row.get("segment_label", ""),
            "arrivals": row.get("arrivals", ""),
            "nights": number(row.get("nights", 0)),
            "total_revenue": money(row.get("total_revenue", 0)),
        }
        for index, row in enumerate(top_repeat_guests, start=1)
    ]
    revenue_modal_body = (
        "<h3>Топ-5 гостей по доходу</h3>"
        + table(
            [
                ("guest_name", "Гость"),
                ("city", "Город"),
                ("segment", "Сегмент"),
                ("total_revenue", "Доход"),
            ],
            [
                {
                    "guest_name": guest_display(row, f"Гость #{index}"),
                    "city": row.get("city_normalized", ""),
                    "segment": row.get("segment_label", ""),
                    "total_revenue": money(row.get("total_revenue", 0)),
                }
                for index, row in enumerate(top_revenue_guests, start=1)
            ],
        )
        + "<h3>Топ-5 городов по доходу</h3>"
        + table(
            [("city_normalized", "Город"), ("guests", "Гостей"), ("total_revenue", "Доход")],
            [
                {
                    **row,
                    "total_revenue": money(row.get("total_revenue", 0)),
                }
                for row in cities[:5]
            ],
        )
        + "<h3>Топ-5 услуг по доходу</h3>"
        + table(
            [("service_name", "Услуга"), ("filled_guests", "Строк"), ("spend", "Сумма")],
            [
                {
                    **row,
                    "spend": money(row.get("spend", 0)),
                }
                for row in services[:5]
            ],
        )
    )
    repeat_modal_body = table(
        [
            ("guest_name", "Гость"),
            ("city", "Город"),
            ("segment", "Сегмент"),
            ("arrivals", "Заездов"),
            ("nights", "Ночей"),
            ("total_revenue", "Доход"),
        ],
        repeat_guest_table_rows,
    )
    no_show_modal_body = table(
        [
            ("guest_name", "Гость"),
            ("city", "Город"),
            ("segment", "Сегмент"),
            ("arrivals", "Заездов"),
            ("nights", "Забронировано ночей"),
            ("total_revenue", "Доход"),
        ],
        no_show_table_rows,
    )

    city_modal_html = []
    city_modal_ids = {}
    for city_index, city in enumerate(cities[:25], start=1):
        city_name = city["city_normalized"]
        modal_id = guest_modal_id("city-modal", city_index)
        city_modal_ids[city_name] = modal_id
        city_guests = sorted(
            [row for row in clean_guests if row.get("city_normalized") == city_name],
            key=lambda row: as_float(row, "total_revenue"),
            reverse=True,
        )[:10]
        city_modal_html.append(
            modal(
                modal_id,
                f"Топ гостей: {city_name}",
                table(
                    [
                        ("guest_name", "Гость"),
                        ("segment", "Сегмент"),
                        ("arrivals", "Заездов"),
                        ("nights", "Ночей"),
                        ("total_revenue", "Доход"),
                    ],
                    [
                        {
                            "guest_name": guest_display(row, f"Гость #{index}"),
                            "segment": row.get("segment_label", ""),
                            "arrivals": row.get("arrivals", ""),
                            "nights": number(row.get("nights", 0)),
                            "total_revenue": money(row.get("total_revenue", 0)),
                        }
                        for index, row in enumerate(city_guests, start=1)
                    ],
                ),
            )
        )

    top_guest_modal_html = []
    top_guest_modal_ids = {}
    for index, row in enumerate(top_guests_raw, start=1):
        modal_id = guest_modal_id("guest-modal", index)
        top_guest_modal_ids[str(index)] = modal_id
        top_guest_modal_html.append(
            modal(
                modal_id,
                guest_display(row, f"Гость #{index}"),
                table(
                    [("metric", "Показатель"), ("value", "Значение")],
                    [
                        {"metric": "Город", "value": row.get("city", "")},
                        {"metric": "Сегмент", "value": row.get("segment", "")},
                        {"metric": "Заездов", "value": row.get("arrivals", "")},
                        {"metric": "Ночей", "value": number(row.get("nights", 0))},
                        {"metric": "Доход от комнат", "value": money(row.get("room_revenue", 0))},
                        {"metric": "Общий доход", "value": money(row.get("total_revenue", 0))},
                        {"metric": "Доход на ночь", "value": money(row.get("revenue_per_night", 0))},
                    ],
                ),
            )
        )

    html_text = f"""<!doctype html>
<html lang="ru">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Utkino Analytics 2025</title>
  <style>
    :root {{
      --bg: #f7f5ef;
      --surface: #ffffff;
      --surface-soft: #fbfaf6;
      --line: #ddd5c2;
      --text: #000000;
      --muted: #665f52;
      --accent: rgb(179, 161, 104);
      --accent-2: #7f7045;
      --header: #111111;
      --warn: #a06f24;
      --warn-bg: #fbf3df;
      --bad: #b91c1c;
      --good: #496b4a;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      background: var(--bg);
      color: var(--text);
      font-family: "Segoe UI", Arial, sans-serif;
      line-height: 1.45;
    }}
    body.modal-open {{
      overflow: hidden;
    }}
    header {{
      background: var(--header);
      color: #fff;
      padding: 28px 32px 24px;
      border-bottom: 4px solid var(--accent);
    }}
    header h1 {{
      margin: 0 0 8px;
      font-size: 28px;
      font-weight: 650;
      letter-spacing: 0;
    }}
    header p {{ margin: 0; color: #d8cfad; }}
    .meta-line {{
      display: flex;
      flex-wrap: wrap;
      gap: 14px;
      margin-top: 14px;
      color: #e8dfbd;
      font-size: 12px;
    }}
    .meta-line strong {{ color: #fff; }}
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
      color: #000;
      font-weight: 650;
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
      border-top: 4px solid var(--accent);
    }}
    .kpi.clickable {{
      position: relative;
      padding-right: 46px;
      background: linear-gradient(180deg, #ffffff 0%, #fffdf7 100%);
    }}
    .kpi.clickable::after {{
      content: "↗";
      position: absolute;
      top: 14px;
      right: 14px;
      width: 24px;
      height: 24px;
      border: 1px solid var(--accent);
      border-radius: 50%;
      display: grid;
      place-items: center;
      color: var(--accent-2);
      font-weight: 700;
      font-size: 13px;
    }}
    .clickable {{
      cursor: pointer;
      transition: border-color 0.15s ease, box-shadow 0.15s ease, transform 0.15s ease;
    }}
    .clickable:hover {{
      border-color: var(--accent);
      box-shadow: 0 6px 20px rgba(0, 0, 0, 0.08);
      transform: translateY(-1px);
    }}
    .kpi-label {{ color: var(--muted); font-size: 13px; }}
    .kpi-value {{ font-size: 24px; font-weight: 700; margin-top: 8px; }}
    .kpi-hint {{ color: var(--muted); font-size: 12px; margin-top: 8px; }}
    .kpi-action {{
      margin-top: 12px;
      color: var(--accent-2);
      font-size: 12px;
      font-weight: 650;
    }}
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
      background: #eee8d7;
      border-radius: 999px;
      overflow: hidden;
    }}
    .bar-fill {{
      height: 100%;
      background: linear-gradient(90deg, var(--accent-2), var(--accent));
    }}
    .bar-value {{ text-align: right; color: var(--muted); }}
    .table-wrap {{ overflow-x: auto; }}
    table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
    th, td {{
      border-bottom: 1px solid var(--line);
      padding: 9px 8px;
      text-align: left;
      vertical-align: top;
    }}
    th {{ color: var(--muted); font-weight: 650; background: var(--surface-soft); }}
    .sortable-table th {{
      cursor: pointer;
      user-select: none;
    }}
    .sortable-table th::after {{
      content: "↕";
      margin-left: 6px;
      color: var(--accent-2);
      font-size: 11px;
    }}
    .sortable-table th.sorted-asc::after {{ content: "↑"; }}
    .sortable-table th.sorted-desc::after {{ content: "↓"; }}
    tr.clickable:hover td {{ background: var(--surface-soft); }}
    .audit-row.status-good td:first-child {{
      border-left: 4px solid var(--good);
    }}
    .audit-row.status-warning td:first-child {{
      border-left: 4px solid var(--warn);
      background: #fff8e8;
    }}
    .audit-row.status-bad td:first-child {{
      border-left: 4px solid var(--bad);
      background: #fff0f0;
    }}
    .audit-row.status-warning td:nth-child(2),
    .audit-row.status-warning td:nth-child(3) {{
      background: #fff8e8;
    }}
    .audit-row.status-bad td:nth-child(2),
    .audit-row.status-bad td:nth-child(3) {{
      background: #fff0f0;
    }}
    .audit-card {{
      border-radius: 8px;
      border: 1px solid var(--line);
      overflow: hidden;
    }}
    .audit-card.status-good {{ border-color: #9eb49f; }}
    .audit-card.status-bad {{ border-color: #d99b9b; background: #fff7f7; }}
    .audit-card .kpi {{ border: 0; border-top: 4px solid var(--line); }}
    .audit-card.status-good .kpi {{ border-top-color: var(--good); }}
    .audit-card.status-bad .kpi {{ border-top-color: var(--bad); }}
    .notice {{
      border-left: 4px solid var(--warn);
      background: var(--warn-bg);
      padding: 12px 14px;
      border-radius: 6px;
      color: #4f3712;
      margin-bottom: 16px;
    }}
    .status-pill {{
      display: inline-block;
      border: 1px solid var(--line);
      border-radius: 999px;
      padding: 3px 8px;
      font-size: 12px;
      color: var(--muted);
      background: var(--surface-soft);
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
    .modal-backdrop {{
      position: fixed;
      inset: 0;
      z-index: 50;
      display: none;
      align-items: center;
      justify-content: center;
      background: rgba(0, 0, 0, 0.56);
      padding: 24px;
    }}
    .modal-backdrop.open {{ display: flex; }}
    .modal {{
      width: min(960px, 100%);
      max-height: min(760px, 90vh);
      overflow: hidden;
      background: var(--surface);
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 22px;
      position: relative;
      display: flex;
      flex-direction: column;
    }}
    .modal .table-wrap {{
      max-height: min(520px, 62vh);
      overflow: auto;
      border: 1px solid var(--line);
      border-radius: 6px;
    }}
    .modal.multi-table .table-wrap {{
      max-height: min(180px, 22vh);
    }}
    .modal.modal-scroll {{
      overflow: auto;
    }}
    .modal.modal-scroll .table-wrap {{
      max-height: none;
      overflow-x: auto;
      overflow-y: visible;
    }}
    .modal thead th {{
      position: sticky;
      top: 0;
      z-index: 1;
    }}
    .modal h2 {{ margin: 0 42px 18px 0; font-size: 21px; }}
    .modal h3 {{ margin: 18px 0 10px; font-size: 15px; }}
    .modal-close {{
      position: absolute;
      top: 12px;
      right: 12px;
      width: 34px;
      height: 34px;
      border: 1px solid var(--line);
      border-radius: 50%;
      background: var(--surface-soft);
      color: var(--text);
      cursor: pointer;
      font-size: 22px;
      line-height: 1;
    }}
    @media (max-width: 980px) {{
      main {{ padding: 18px; }}
      .span-3, .span-4, .span-6, .span-8 {{ grid-column: span 12; }}
      .bar-row {{ grid-template-columns: 1fr; gap: 5px; }}
      .bar-value {{ text-align: left; }}
      .modal-backdrop {{ padding: 12px; }}
      .modal {{ max-height: 92vh; padding: 18px; }}
      .modal .table-wrap {{ max-height: 60vh; }}
      .modal.multi-table .table-wrap {{ max-height: 18vh; }}
    }}
  </style>
</head>
<body>
  <header>
    <h1>Utkino Analytics 2025</h1>
    <p>Аналитический отчет по гостям, выручке, сегментам и качеству данных</p>
    <div class="meta-line">{metadata_html}</div>
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
        <div class="span-3">{kpi_card("Общий доход", money(summary["total_revenue"]), "Источник: аналитика 2025", "revenue-modal")}</div>
        <div class="span-3">{kpi_card("Гостей", number(summary["guest_count"]), f"{number(summary['arrivals'])} заездов")}</div>
        <div class="span-3">{kpi_card("Ночей", number(summary["nights"]), f"{money(summary['average_revenue_per_night'])} на ночь")}</div>
        <div class="span-3">{kpi_card("Повторные гости", percent(summary["repeat_guest_share"]), f"{percent(summary['repeat_revenue_share'])} выручки", "repeat-modal")}</div>
        <div class="panel span-6">
          <h2>Выручка по сегментам</h2>
          {bar_chart(segments, "segment_label", "total_revenue", money, 6)}
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
          <h2>CLUB-сегменты</h2>
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
          <h2>Города по доходу</h2>
          {bar_chart(cities, "city_normalized", "total_revenue", money, 12)}
        </div>
        <div class="panel span-4">
          <h2>Качество географии</h2>
          {kpi_card("Без города", percent(data_quality["missing_city_share"]), f"{data_quality['missing_city_count']} гостей")}
        </div>
        <div class="panel span-12">
          {table([
              ("city_normalized", "Город"),
              ("guests", "Гостей"),
              ("arrivals", "Заездов"),
              ("nights", "Ночей"),
              ("total_revenue", "Доход"),
              ("average_revenue_per_guest", "Доход на гостя"),
          ], city_table_rows, 25, lambda row, index: (
              f'class="clickable" data-modal-open="{esc(city_modal_ids.get(row["city_normalized"], ""))}"'
          ))}
        </div>
      </div>
    </section>

    <section id="loyalty" class="section">
      <div class="grid">
        <div class="panel span-6">
          <h2>Выручка по числу заездов</h2>
          {bar_chart(repeat, "arrival_group_label", "total_revenue", money, 3)}
        </div>
        <div class="panel span-6">
          <h2>No-show бронирования</h2>
          {kpi_card("No-show", number(data_quality["no_show_booking_count"]), money(data_quality["no_show_booking_revenue"]), "no-show-modal")}
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
        <div class="panel span-8">
          <h2>Дополнительные услуги</h2>
          {bar_chart(services, "service_name", "spend", money, 10)}
        </div>
        <div class="panel span-4">
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
        ], top_guests, None, lambda row, index: (
            f'class="clickable" data-modal-open="{esc(top_guest_modal_ids.get(str(index + 1), ""))}"'
        ), table_class="sortable-table")}
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
          ], reliability_rows, None, lambda row, index: (
              f'class="audit-row {esc(status_class(row.get("status_code", "")))}"'
          ))}
        </div>
        <div class="panel span-6">
          <h2>Межлистовая сверка</h2>
          <div class="audit-card {esc("status-bad" if reconciliation["row_level_mismatch_count"] else "status-good")}">
            {kpi_card("Расхождений", number(reconciliation["row_level_mismatch_count"]), "Основной лист остается источником финансов")}
          </div>
          <p>Сумма основного листа: <strong>{money(reconciliation["main_total_revenue"])}</strong></p>
          <p>Сумма листа категорий: <strong>{money(reconciliation["category_total_revenue"])}</strong></p>
        </div>
      </div>
    </section>
  </main>
  {modal("revenue-modal", "Общий доход: основные источники", revenue_modal_body)}
  {modal("repeat-modal", "Повторные гости", repeat_modal_body)}
  {modal("no-show-modal", "No-show бронирования", no_show_modal_body)}
  {''.join(city_modal_html)}
  {''.join(top_guest_modal_html)}
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

    const parseSortableValue = (value) => {{
      const text = value.trim();
      const numeric = text
        .replace(/\\s/g, "")
        .replace(/[₽%]/g, "")
        .replace(",", ".")
        .replace(/[^\\d.-]/g, "");
      if (numeric && numeric !== "-" && !Number.isNaN(Number(numeric))) {{
        return Number(numeric);
      }}
      return text.toLowerCase();
    }};
    document.querySelectorAll(".sortable-table").forEach((table) => {{
      table.querySelectorAll("th").forEach((header, columnIndex) => {{
        header.addEventListener("click", () => {{
          const tbody = table.querySelector("tbody");
          const direction = header.dataset.direction === "asc" ? "desc" : "asc";
          table.querySelectorAll("th").forEach((item) => {{
            item.classList.remove("sorted-asc", "sorted-desc");
            delete item.dataset.direction;
          }});
          header.dataset.direction = direction;
          header.classList.add(direction === "asc" ? "sorted-asc" : "sorted-desc");

          const rows = Array.from(tbody.querySelectorAll("tr"));
          rows.sort((left, right) => {{
            const leftValue = parseSortableValue(left.children[columnIndex]?.innerText || "");
            const rightValue = parseSortableValue(right.children[columnIndex]?.innerText || "");
            const result = typeof leftValue === "number" && typeof rightValue === "number"
              ? leftValue - rightValue
              : String(leftValue).localeCompare(String(rightValue), "ru");
            return direction === "asc" ? result : -result;
          }});
          rows.forEach((row) => tbody.appendChild(row));
        }});
      }});
    }});

    const modalButtons = document.querySelectorAll("[data-modal-open]");
    const closeButtons = document.querySelectorAll("[data-modal-close]");
    const updateModalLock = () => {{
      const hasOpenModal = document.querySelector(".modal-backdrop.open");
      document.body.classList.toggle("modal-open", Boolean(hasOpenModal));
    }};
    const openModal = (id) => {{
      if (!id) return;
      const modal = document.getElementById(id);
      if (!modal) return;
      modal.classList.add("open");
      modal.setAttribute("aria-hidden", "false");
      updateModalLock();
    }};
    const closeModal = (modal) => {{
      if (!modal) return;
      modal.classList.remove("open");
      modal.setAttribute("aria-hidden", "true");
      updateModalLock();
    }};
    modalButtons.forEach((button) => {{
      button.addEventListener("click", () => openModal(button.dataset.modalOpen));
    }});
    closeButtons.forEach((button) => {{
      button.addEventListener("click", () => closeModal(button.closest(".modal-backdrop")));
    }});
    document.querySelectorAll(".modal-backdrop").forEach((backdrop) => {{
      backdrop.addEventListener("click", (event) => {{
        if (event.target === backdrop) closeModal(backdrop);
      }});
    }});
    document.addEventListener("keydown", (event) => {{
      if (event.key === "Escape") {{
        document.querySelectorAll(".modal-backdrop.open").forEach(closeModal);
      }}
    }});
  </script>
</body>
</html>
"""

    output_file.parent.mkdir(parents=True, exist_ok=True)
    output_file.write_text(html_text, encoding="utf-8")
    return output_file
