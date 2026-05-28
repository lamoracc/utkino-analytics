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
          ], city_table_rows, 25)}
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
