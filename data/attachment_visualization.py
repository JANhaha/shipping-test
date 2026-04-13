import re
from urllib.parse import unquote

from data.gmail_store import list_attachments_for_message_ids, list_messages


CATEGORY_ORDER = ["指数类", "航线日报", "FFA", "矿石煤焦", "成交报告", "其他"]
ROUTE_CODE_PATTERN = re.compile(r"\b([A-Z]{1,4}\d{1,2}[A-Z]?_[0-9]{2})\b")


def build_attachment_dashboard(limit=300):
    latest_messages = list_messages(limit=1)
    if not latest_messages:
        return {"categories": [], "total": 0}

    latest_message = latest_messages[0]
    latest_message_id = latest_message["gmail_message_id"]
    attachments = list_attachments_for_message_ids([latest_message_id]).get(latest_message_id, [])[:limit]

    grouped = {}
    for raw in attachments:
        raw["sender"] = latest_message.get("sender")
        raw["subject"] = latest_message.get("subject")
        raw["received_at"] = latest_message.get("received_at")
        raw["gmail_message_id"] = latest_message_id
        item = _enrich_attachment(raw)
        grouped.setdefault(item["business_category"], []).append(item)

    categories = []
    for name in CATEGORY_ORDER:
        items = grouped.pop(name, [])
        if items:
            categories.append({"name": name, "count": len(items), "items": items})
    for name in sorted(grouped.keys()):
        categories.append({"name": name, "count": len(grouped[name]), "items": grouped[name]})

    return {"categories": categories, "total": len(attachments)}


def _enrich_attachment(item):
    text = _clean_text(item.get("parsed_text") or "")
    filename = unquote(item.get("filename") or "")
    return {
        **item,
        "parsed_text": text,
        "display_name": filename,
        "business_category": _business_category(filename, text),
        "report_type": _report_type(filename, text),
        "headline_metrics": _headline_metrics(filename, text),
        "table": _extract_table(filename, text),
        "selected_cards": _selected_cards(filename, text),
        "summary": _summary_from_metrics(filename, text),
    }


def _business_category(filename, text):
    name = filename.lower()
    lower = text.lower()
    if "fixture" in name:
        return "成交报告"
    if "ffa" in name or "freight futures" in lower:
        return "FFA"
    if "metals" in name or "coking coal" in lower or "iron ore" in lower:
        return "矿石煤焦"
    if "report" in name and any(word in name for word in ["capesize", "panamax", "handysize", "supramax", "dry cargo"]):
        return "航线日报"
    if "index" in name or "baltic" in name:
        return "指数类"
    return "其他"


def _report_type(filename, text):
    name = filename.lower()
    if "capesize" in name:
        return "Capesize"
    if "panamax" in name:
        return "Panamax"
    if "handysize" in name:
        return "Handysize"
    if "supramax" in name:
        return "Supramax"
    if "fixture" in name:
        return "Fixtures"
    if "metals" in name:
        return "Metals & Coking Coal"
    if "ffa" in name:
        return "Dry FFA"
    if "dry cargo" in name:
        return "Dry Cargo"
    if "baltic" in name and "index" in name:
        return "Baltic Index"
    return "General"


def _headline_metrics(filename, text):
    metrics = []
    patterns = [
        ("BDI", r"\bBDI\b\s*[: ]\s*([0-9,]+)(?:\s*([-+][0-9.,]+))?"),
        ("BCI", r"\bBCI\b(?:\s*\d+)?\s*[: ]\s*([0-9,]+)(?:\s*([-+][0-9.,]+))?"),
        ("BPI", r"\bBPI\b\s*[: ]\s*([0-9,]+)(?:\s*([-+][0-9.,]+))?"),
        ("BSI", r"\bBSI\b\s*[: ]\s*([0-9,]+)(?:\s*([-+][0-9.,]+))?"),
        ("BHSI", r"\bBHSI\b(?:\d+)?\s*[: ]\s*([0-9,]+)(?:\s*([-+][0-9.,]+))?"),
        ("BCTI", r"\bBCTI\b\s*([0-9,]+)(?:\s*([-+][0-9.,]+))?"),
        ("BDTI", r"\bBDTI\b\s*([0-9,]+)(?:\s*([-+][0-9.,]+))?"),
        ("Brent", r"Brent(?: Crude Oil| UK Oil)?\s*[: ]\s*([0-9.,]+)(?:\s*([-+][0-9.,]+))?"),
        ("Iron Ore", r"Iron Ore(?: TSI 62%)?\s*[: ]\s*([0-9.,-]+)(?:\s*([-+][0-9.,]+))?"),
        ("SOFR", r"S\.?O\.?F\.?R\.?\s*([0-9.,]+)(?:\s*([-+][0-9.,]+))?"),
        ("USD/RMB", r"USD/RMB\s*([0-9.,]+)(?:\s*([-+][0-9.,%]+))?"),
        ("USD/JPY", r"USD/JPY\s*([0-9.,]+)(?:\s*([-+][0-9.,%]+))?"),
        ("GBP/USD", r"GBP/USD\s*([0-9.,]+)(?:\s*([-+][0-9.,%]+))?"),
    ]
    for label, pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            metrics.append({"label": label, "value": match.group(1), "change": match.group(2) if match.lastindex and match.lastindex >= 2 else None})

    unique = []
    seen = set()
    for metric in metrics:
        key = (metric["label"], metric["value"], metric.get("change"))
        if key not in seen:
            seen.add(key)
            unique.append(metric)
    return unique[:10]


def _extract_table(filename, text):
    lower = filename.lower()
    if "baltic" in lower and "index" in lower:
        return _extract_route_table(text)
    if "dry cargo" in lower:
        return _extract_futures_table(text)
    if "metals" in lower:
        return _extract_metals_table(text)
    if "fixture" in lower:
        return _extract_fixtures_table(text)
    return _extract_route_table(text)


def _extract_route_table(text):
    segments = []
    matches = list(ROUTE_CODE_PATTERN.finditer(text))
    for idx, match in enumerate(matches):
        start = match.start()
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(text)
        segment = text[start:end].strip()
        if segment:
            segments.append(segment)

    rows = []
    seen = set()
    for segment in segments:
        code_match = ROUTE_CODE_PATTERN.match(segment)
        if not code_match:
            continue
        code = code_match.group(1)
        rest = segment[len(code):].strip()
        rest = rest.split(" Timecharter")[0].split(" Weighted")[0].strip()
        number_matches = list(re.finditer(r"[-+]?\d[\d,]*(?:\.\d+)?", rest))
        if len(number_matches) < 2:
            continue
        if len(number_matches) >= 3:
            value_match = number_matches[-2]
            change_match = number_matches[-1]
        else:
            value_match = number_matches[-2]
            change_match = number_matches[-1]
        route = rest[:value_match.start()].strip(" -")
        value = value_match.group(0)
        change = change_match.group(0)
        key = (code, route, value, change)
        if route and key not in seen:
            seen.add(key)
            rows.append([code, route, value, change])

    if not rows:
        return None
    return {
        "title": "航线明细",
        "columns": ["航线代码", "航线", "数值", "涨跌"],
        "rows": rows,
    }


def _extract_futures_table(text):
    instruments = [
        ("Capesize (180k dwt) 5 TC", "Capesize 5TC"),
        ("Panamax (82k dwt) 5 TC", "Panamax 5TC"),
        ("Supramax (63.5k dwt) 11 TC", "Supramax 11TC"),
        ("Handysize (38k dwt) 7 TC", "Handysize 7TC"),
    ]
    rows = []
    for marker, label in instruments:
        block = _slice_block(text, marker)
        if not block:
            continue
        for tenor in ["Mar 26", "Apr 26", "May 26", "Jun 26", "Q2 26", "Q3 26", "Cal 27"]:
            match = re.search(re.escape(tenor) + r"\s+([0-9,]+)\s+([0-9,]+)", block, flags=re.IGNORECASE)
            if match:
                rows.append([label, tenor, match.group(1), match.group(2)])
    if not rows:
        return None
    return {
        "title": "FFA / Freight Futures",
        "columns": ["品种", "期限", "上期", "本期"],
        "rows": rows,
    }


def _extract_metals_table(text):
    rows = []
    for tenor in ["Mar 26", "Apr 26", "May 26", "Jun 26"]:
        match = re.search(
            re.escape(tenor) + r"\s+([0-9.]+)\s+[0-9.]+\s+([0-9.]+)\s+[0-9.]+\s+([0-9.]+)\s+[0-9.]+\s+([0-9,]+)\s+0\s+([0-9.]+)",
            text,
            flags=re.IGNORECASE,
        )
        if match:
            rows.append([tenor, match.group(1), match.group(2), match.group(3), match.group(4), match.group(5)])
    if not rows:
        return None
    return {
        "title": "矿石与煤焦月度报价",
        "columns": ["月份", "62% Iron Ore", "Lump Premium", "MBIOI65%", "US HRC", "Coking Coal"],
        "rows": rows,
    }


def _extract_fixtures_table(text):
    rows = []
    pattern = re.compile(
        r"'([^']+)'\s+(\d{4})\s+([0-9]{4,6})\s+dwt\s+dely\s+(.+?)\s+\$([0-9,]+(?:\+[0-9,]+bb)?)",
        flags=re.IGNORECASE,
    )
    for match in pattern.finditer(text):
        rows.append([match.group(1), match.group(3), match.group(4).strip(), match.group(5)])
    if not rows:
        return None
    return {
        "title": "成交样本",
        "columns": ["船名", "载重吨", "航次/区域", "成交水平"],
        "rows": rows,
    }


def _selected_cards(filename, text):
    lower = filename.lower()
    if "capesize" in lower:
        return _extract_market_cards(text, [("Pacific", "Pacific"), ("Atlantic", "Atlantic"), ("Market Comments", "Market Comments")])
    if "panamax" in lower:
        return _extract_market_cards(text, [("Atlantic", "Atlantic"), ("Pacific", "Pacific"), ("MID EAST", "Mid East"), ("Market Comments", "Market Comments")])
    if "handysize" in lower or "supramax" in lower:
        return _extract_market_cards(text, [("ATLANTIC", "Atlantic"), ("PACIFIC", "Pacific"), ("Market Comments", "Market Comments")])
    if "dry cargo" in lower:
        return _extract_market_cards(text, [("Exchange Rates", "Exchange Rates"), ("Freight Futures", "Freight Futures"), ("Bunker Prices", "Bunker Prices")])
    return []


def _extract_market_cards(text, markers):
    cards = []
    for index, (marker, title) in enumerate(markers):
        start_match = re.search(re.escape(marker) + r"\s*:?\s*", text, flags=re.IGNORECASE)
        if not start_match:
            continue
        start = start_match.end()
        end = len(text)
        for next_marker, _ in markers[index + 1:]:
            next_match = re.search(re.escape(next_marker) + r"\s*:?\s*", text[start:], flags=re.IGNORECASE)
            if next_match:
                end = start + next_match.start()
                break
        content = text[start:end].strip(" :-")
        if content:
            cards.append({
                "title": title,
                "content": _compress_text(content, limit=560),
            })
    return cards[:4]


def _slice_block(text, marker):
    start = text.find(marker)
    if start < 0:
        return ""
    tail = text[start:]
    nearest = len(tail)
    for next_marker in ["Panamax (82k dwt) 5 TC", "Supramax (63.5k dwt) 11 TC", "Handysize (38k dwt) 7 TC", "Bunker Prices"]:
        if next_marker == marker:
            continue
        pos = tail.find(next_marker)
        if pos > 0:
            nearest = min(nearest, pos)
    return tail[:nearest]


def _summary_from_metrics(filename, text):
    metrics = _headline_metrics(filename, text)
    if metrics:
        parts = []
        for metric in metrics[:4]:
            suffix = f" ({metric['change']})" if metric.get("change") else ""
            parts.append(f"{metric['label']} {metric['value']}{suffix}")
        return " / ".join(parts)
    cards = _selected_cards(filename, text)
    if cards:
        return " / ".join(f"{card['title']}: {card['content'][:80]}" for card in cards[:2])
    return _compress_text(text, limit=220)


def _compress_text(text, limit=220):
    value = re.sub(r"\s+", " ", text).strip()
    return value[:limit] + ("..." if len(value) > limit else "")


def _clean_text(text):
    text = text.replace("\u00a1", " ")
    text = text.replace("\ufb00", "ff").replace("\ufb01", "fi").replace("\ufb02", "fl")
    replacements = {
        "Inde x": "Index",
        "P anamax": "Panamax",
        "Kam sarm ax": "Kamsarmax",
        "Rout e": "Route",
        "da y": "day",
        "Paciﬁc": "Pacific",
        "oﬀ": "off",
        "ﬁxing": "fixing",
        "ﬁxed": "fixed",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    text = text.replace("↑", " ↑ ").replace("↓", " ↓ ").replace("→", " → ")
    return re.sub(r"\s+", " ", text).strip()
