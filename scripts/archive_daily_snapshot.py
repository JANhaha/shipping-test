import json
import sys
import csv
import base64
import os
import shutil
import subprocess
from datetime import datetime, timedelta, timezone
from html import escape
from pathlib import Path
from urllib.request import urlopen


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from data.shipping_data_payload import build_shipping_data_payload
from data.dashboard_service import ShippingDashboardService
from data.gmail_store import init_db
from data.map_data_service import BalticMapDataService


BEIJING_TZ = timezone(timedelta(hours=8), name="Asia/Shanghai")
REMOTE_DATA_REF = "stable"
REMOTE_DATA_BASE = f"https://raw.githubusercontent.com/JANhaha/shipping-test/{REMOTE_DATA_REF}/docs/data"
SNAPSHOT_RETENTION_DAYS = int(os.getenv("SNAPSHOT_RETENTION_DAYS", "14"))


def main() -> None:
    init_db()
    now = datetime.now(BEIJING_TZ)
    payload = {
        "archived_at": now.isoformat(),
        "timezone": "Asia/Shanghai",
        "data_sources": {},
        "dashboard": load_or_build("dashboard.json", lambda: ShippingDashboardService().get_dashboard()),
        "shipping_data": load_or_build(
            "shipping_data.json", lambda: build_shipping_data_payload(limit=300)
        ),
        "map_data": load_or_build("map_data.json", lambda: BalticMapDataService().get_map_data()),
    }

    target_dir = ROOT / "data" / "daily_snapshots"
    target_dir.mkdir(parents=True, exist_ok=True)
    date_key = f"{now:%Y-%m-%d}"
    snapshot_key = date_key
    json_target = target_dir / f"{snapshot_key}.json"
    html_target = target_dir / f"{snapshot_key}.html"
    if json_target.exists() or html_target.exists():
        snapshot_key = f"{date_key}-{now:%H%M%S}"
        json_target = target_dir / f"{snapshot_key}.json"
        html_target = target_dir / f"{snapshot_key}.html"
    csv_dir = target_dir / snapshot_key
    csv_dir.mkdir(parents=True, exist_ok=True)

    json_target.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    csv_files = write_csv_tables(payload, csv_dir)
    html_target.write_text(render_html_report(payload, csv_files, snapshot_key), encoding="utf-8")
    prune_old_snapshots(target_dir, now, SNAPSHOT_RETENTION_DAYS)
    print(f"wrote {json_target}")
    print(f"wrote {html_target}")


def prune_old_snapshots(target_dir: Path, now: datetime, retention_days: int) -> None:
    if retention_days <= 0:
        return
    cutoff = now.date() - timedelta(days=retention_days)
    for path in target_dir.iterdir():
        snapshot_date = parse_snapshot_date(path.name)
        if snapshot_date is None or snapshot_date >= cutoff:
            continue
        if path.is_dir():
            shutil.rmtree(path)
        else:
            path.unlink()


def parse_snapshot_date(name: str):
    try:
        return datetime.strptime(name[:10], "%Y-%m-%d").date()
    except ValueError:
        return None


def load_or_build(filename: str, builder):
    remote_payload = load_remote_with_github_cli(filename)
    if remote_payload is not None:
        return remote_payload

    remote_url = f"{REMOTE_DATA_BASE}/{filename}"
    try:
        with urlopen(remote_url, timeout=20) as response:
            return json.loads(response.read().decode("utf-8"))
    except Exception:
        pass

    source = ROOT / "docs" / "data" / filename
    if source.exists():
        try:
            return json.loads(source.read_text(encoding="utf-8"))
        except Exception:
            pass
    return builder()


def load_remote_with_github_cli(filename: str):
    gh = Path(r"C:\Program Files\GitHub CLI\gh.exe")
    if not gh.exists():
        return None
    path = f"docs/data/{filename}"
    try:
        result = subprocess.run(
            [
                str(gh),
                "api",
                f"repos/JANhaha/shipping-test/contents/{path}?ref={REMOTE_DATA_REF}",
                "--jq",
                ".content",
            ],
            cwd=ROOT,
            text=True,
            capture_output=True,
            timeout=30,
            check=True,
        )
        encoded = "".join(result.stdout.split())
        return json.loads(base64.b64decode(encoded).decode("utf-8"))
    except Exception:
        return None


def write_csv_tables(payload: dict, csv_dir: Path) -> list[Path]:
    files = []
    tables = {
        "shipping_indices.csv": shipping_indices_rows(payload),
        "crude.csv": crude_rows(payload),
        "forex.csv": forex_rows(payload),
        "bunker_prices.csv": bunker_rows(payload),
        "cbfi.csv": cbfi_rows(payload),
        "map_routes.csv": map_route_rows(payload),
        "shipping_data_tables.csv": shipping_data_rows(payload),
    }
    for filename, rows in tables.items():
        if not rows:
            continue
        target = csv_dir / filename
        with target.open("w", newline="", encoding="utf-8-sig") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)
        files.append(target)
    return files


def shipping_indices_rows(payload: dict) -> list[dict]:
    rows = []
    for item in payload.get("dashboard", {}).get("baltic", {}).get("data", []) or []:
        rows.append(
            {
                "code": item.get("code"),
                "name": item.get("name"),
                "value": item.get("value"),
                "change": item.get("change"),
                "daily_percent": item.get("daily_percent"),
                "date": item.get("date"),
            }
        )
    return rows


def crude_rows(payload: dict) -> list[dict]:
    crude = payload.get("dashboard", {}).get("crude", {}) or {}
    return [
        {
            "code": item.get("code"),
            "name": item.get("name"),
            "latest": item.get("latest"),
            "open": item.get("open"),
            "previous_close": item.get("previous_close"),
            "change_from_open": item.get("change_from_open"),
            "change_percent_from_open": item.get("change_percent_from_open"),
        }
        for item in crude.values()
        if isinstance(item, dict)
    ]


def forex_rows(payload: dict) -> list[dict]:
    forex = payload.get("dashboard", {}).get("forex", {}) or {}
    return [
        {
            "code": item.get("code"),
            "title": item.get("title"),
            "latest": item.get("latest"),
            "open": item.get("open"),
            "previous_close": item.get("previous_close"),
            "change_from_open": item.get("change_from_open"),
            "change_percent_from_open": item.get("change_percent_from_open"),
        }
        for item in forex.values()
        if isinstance(item, dict)
    ]


def bunker_rows(payload: dict) -> list[dict]:
    rows = []
    for item in payload.get("dashboard", {}).get("bunker_index", {}).get("ports", []) or []:
        rows.append(
            {
                "port": item.get("port"),
                "country": item.get("country"),
                "ifo380": item.get("ifo380"),
                "vlsfo": item.get("vlsfo"),
                "mgo": item.get("mgo"),
                "date": item.get("date"),
            }
        )
    return rows


def cbfi_rows(payload: dict) -> list[dict]:
    rows = []
    for item in payload.get("dashboard", {}).get("cbfi", {}).get("routes", []) or []:
        rows.append(
            {
                "route": item.get("route"),
                "ship_type": item.get("ship_type"),
                "previous": item.get("previous"),
                "current": item.get("current"),
                "change_percent": item.get("change_percent"),
            }
        )
    return rows


def map_route_rows(payload: dict) -> list[dict]:
    rows = []
    for segment in payload.get("map_data", {}).get("segments", []) or []:
        for index in segment.get("indexes", []) or []:
            for route in index.get("routes", []) or []:
                market = route.get("market_data") or {}
                rows.append(
                    {
                        "segment": segment.get("title"),
                        "index": index.get("title"),
                        "code": route.get("code"),
                        "route": route.get("tooltip") or route.get("description"),
                        "latest_value": market.get("value"),
                        "change": market.get("change"),
                        "source_report": market.get("source_report"),
                        "received_at": market.get("received_at"),
                    }
                )
    return rows


def shipping_data_rows(payload: dict) -> list[dict]:
    rows = []
    for category in payload.get("shipping_data", {}).get("attachment_categories", []) or []:
        for item in category.get("items", []) or []:
            table = item.get("table") or {}
            columns = table.get("columns") or []
            for row in table.get("rows") or []:
                values = dict(zip(columns, row))
                rows.append(
                    {
                        "category": category.get("name"),
                        "report_type": item.get("report_type"),
                        "table": table.get("title"),
                        "col_1": column_value(values, columns, row, 0),
                        "col_2": column_value(values, columns, row, 1),
                        "col_3": column_value(values, columns, row, 2),
                        "col_4": column_value(values, columns, row, 3),
                        "col_5": column_value(values, columns, row, 4),
                        "col_6": column_value(values, columns, row, 5),
                    }
                )
    return rows


def column_value(values: dict, columns: list, row: list, index: int):
    if index < len(columns):
        return values.get(columns[index], "")
    if index < len(row):
        return row[index]
    return ""


def render_html_report(payload: dict, csv_files: list[Path], date_key: str) -> str:
    dashboard = payload.get("dashboard", {})
    shipping = payload.get("shipping_data", {})
    map_data = payload.get("map_data", {})
    source = shipping.get("source_message") or dashboard.get("source_message") or {}
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Daily Shipping Snapshot {escape(payload.get('archived_at', '')[:10])}</title>
  <style>
    body{{margin:0;background:#f5efe7;color:#17262d;font-family:"Segoe UI","Microsoft YaHei",sans-serif}}
    .shell{{max-width:1380px;margin:0 auto;padding:28px 18px 48px}}
    .hero,.panel{{background:#fffdf9;border:1px solid rgba(20,36,43,.12);border-radius:22px;box-shadow:0 18px 42px rgba(20,36,43,.08);padding:22px;margin-bottom:18px}}
    h1,h2,h3,p{{margin:0}} h1{{font-size:34px}} h2{{font-size:22px;margin-bottom:12px}} h3{{font-size:16px;margin-bottom:8px}}
    .meta{{color:#667983;font-size:13px;line-height:1.8;margin-top:10px}}
    .grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:14px}}
    .card{{background:#f8fbfc;border:1px solid rgba(11,89,105,.12);border-radius:16px;padding:14px}}
    .label{{font-size:12px;color:#667983}} .value{{font-size:25px;font-weight:800;margin-top:6px}}
    .up{{color:#00b050;font-weight:800}} .down{{color:#ff3b30;font-weight:800}}
    .table-wrap{{overflow:auto;border:1px solid rgba(20,36,43,.12);border-radius:16px;background:#fff;margin-top:12px}}
    table{{width:100%;border-collapse:collapse;font-size:13px}} th,td{{padding:10px;border-bottom:1px solid rgba(20,36,43,.1);text-align:left;vertical-align:top}} th{{background:#eef6f8;color:#47636d}}
    .links a{{display:inline-block;margin:6px 8px 0 0;padding:8px 11px;border-radius:999px;background:#0b5969;color:white;text-decoration:none;font-size:12px}}
  </style>
</head>
<body>
  <div class="shell">
    <section class="hero">
      <h1>每日航运数据归档</h1>
      <div class="meta">归档时间：{escape(payload.get('archived_at', ''))} 北京时间</div>
      <div class="meta">源邮件：{escape(str(source.get('subject') or '-'))} / 接收时间：{escape(str(source.get('received_at') or '-'))}</div>
      <div class="links">{''.join(f'<a href="{escape(path.parent.name + "/" + path.name)}">{escape(path.name)}</a>' for path in csv_files)}</div>
    </section>
    {section('数据抓取状态', table_html(status_rows(payload)))}
    {section('航运相关指数', card_grid(shipping_indices_rows(payload), ['code','value','change','daily_percent','date']))}
    {section('原油信息', card_grid(crude_rows(payload), ['name','latest','open','change_from_open','change_percent_from_open']))}
    {section('相关汇率信息', table_html(forex_rows(payload)))}
    {section('全球主要港口油价', table_html(bunker_rows(payload)))}
    {section('中国沿海散货运价指数', table_html(cbfi_rows(payload)))}
    {section('MAP DATA 航线金额', table_html([row for row in map_route_rows(payload) if row.get('latest_value')]))}
    {section('Shipping Data 附件表格', table_html(shipping_data_rows(payload)))}
    {section('原始数据索引', raw_data_links(date_key))}
  </div>
</body>
</html>"""


def status_rows(payload: dict) -> list[dict]:
    dashboard = payload.get("dashboard", {}) or {}
    rows = [
        status_row("航运相关指数", dashboard.get("baltic")),
        status_row("中国沿海散货运价指数", dashboard.get("cbfi")),
        status_row("进口矿指数", dashboard.get("iron_ore")),
        status_row("中行美元折算价", dashboard.get("boc_usd")),
        status_row("全球主要港口油价", dashboard.get("bunker_index")),
    ]
    for code, item in (dashboard.get("crude") or {}).items():
        rows.append(status_row(f"原油 {code}", item))
    for code, item in (dashboard.get("forex") or {}).items():
        rows.append(status_row(f"汇率 {code}", item))
    rows.append(status_row("Shipping Data", payload.get("shipping_data")))
    rows.append(status_row("MAP DATA", payload.get("map_data")))
    return rows


def status_row(name: str, item) -> dict:
    if not isinstance(item, dict):
        return {"section": name, "status": "missing", "updated_at": "", "message": "无数据"}
    error = item.get("error")
    note = item.get("note")
    return {
        "section": name,
        "status": "error" if error else "ok",
        "updated_at": item.get("updated_at") or item.get("served_at") or "",
        "message": error or note or "",
    }


def raw_data_links(date_key: str) -> str:
    return (
        '<div class="links">'
        f'<a href="{escape(date_key)}.json">完整 JSON 快照</a>'
        f'<a href="{escape(date_key)}/shipping_indices.csv">航运指数 CSV</a>'
        f'<a href="{escape(date_key)}/map_routes.csv">MAP 航线 CSV</a>'
        f'<a href="{escape(date_key)}/shipping_data_tables.csv">Shipping Data CSV</a>'
        "</div>"
    )


def section(title: str, body: str) -> str:
    return f'<section class="panel"><h2>{escape(title)}</h2>{body}</section>'


def card_grid(rows: list[dict], fields: list[str]) -> str:
    if not rows:
        return '<div class="meta">暂无数据</div>'
    cards = []
    for row in rows:
        title = row.get(fields[0], "-")
        value = row.get(fields[1], "-") if len(fields) > 1 else "-"
        details = " / ".join(f"{field}: {format_value(row.get(field))}" for field in fields[2:])
        cards.append(f'<div class="card"><div class="label">{escape(str(title))}</div><div class="value">{format_value(value)}</div><div class="meta">{escape(details)}</div></div>')
    return f'<div class="grid">{"".join(cards)}</div>'


def table_html(rows: list[dict]) -> str:
    if not rows:
        return '<div class="meta">暂无数据</div>'
    columns = list(rows[0].keys())
    head = "".join(f"<th>{escape(str(col))}</th>" for col in columns)
    body = []
    for row in rows:
        body.append("<tr>" + "".join(f"<td>{format_value(row.get(col))}</td>" for col in columns) + "</tr>")
    return f'<div class="table-wrap"><table><thead><tr>{head}</tr></thead><tbody>{"".join(body)}</tbody></table></div>'


def format_value(value) -> str:
    if value is None or value == "":
        return "-"
    if isinstance(value, (int, float)):
        return f"{value:.2f}"
    return escape(str(value))


if __name__ == "__main__":
    main()
