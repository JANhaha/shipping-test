"""Read public shipping report metadata and selected factual observations."""

import re
from datetime import datetime, timedelta, timezone
from unicodedata import normalize
from urllib.parse import urljoin, urlsplit

import requests
from bs4 import BeautifulSoup


MYSTEEL_REPORTS_URL = "https://haiyun.mysteel.com/article/p-2871-------------1.html"
BEIJING_TIME = timezone(timedelta(hours=8))
ARTICLE_PATH = re.compile(r"/a/([0-9]{6})[0-9]{2}/[A-Fa-f0-9]{16}\.html")
REPORT_TITLE = re.compile(r"[0-9]{1,2}月[0-9]{1,2}日国际干散货航运市场日报")
REQUEST_HEADERS = {
    "User-Agent": "MandarineOceanReportIndex/1.0 (+https://www.mandarineocean.cn)",
    "Accept": "text/html",
    "Accept-Language": "zh-CN,zh;q=0.9",
}
ROUTES = {
    "C5": ("西澳黑德兰 → 青岛", r"(?<![A-Z0-9])C5(?![A-Z0-9])|黑德兰(?:港)?\s*(?:至|到|-|—)\s*(?:中国)?青岛"),
    "C3": ("巴西图巴朗 → 青岛", r"(?<![A-Z0-9])C3(?![A-Z0-9])|图巴朗(?:港)?\s*(?:至|到|-|—)\s*(?:中国)?青岛"),
    "MP11": ("巴拿马型船航线", r"(?<![A-Z0-9])MP11(?![A-Z0-9])"),
}
ROUTE_PATTERN = re.compile("|".join(f"(?P<{code}>{pattern})" for code, (_, pattern) in ROUTES.items()), re.I)
AMOUNT_PATTERN = re.compile(
    r"(?P<direction>上涨|下跌|上升|下降|上调|下调|涨|跌|升|降|增加|减少)?\s*"
    r"(?P<number>[+-]?\s*(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?)"
    r"\s*美元(?:\s*/\s*(?P<unit>吨|天|日))?"
)
MARKET_SIGNALS = (
    ("盘面分化", r"分化"),
    ("市场偏强", r"稳中(?:向好|走强|偏强)|整体(?:上涨|走强)|情绪偏强|表现强势|稳中有升"),
    ("市场偏弱", r"偏弱|低迷|整体回落|走软|疲软|弱势"),
    ("交投偏淡", r"交投清淡|成交冷清"),
    ("运行平稳", r"基本平稳|整体平稳|整体持稳"),
)


class MysteelReportError(RuntimeError):
    """The public index could not supply a valid report list."""


def parse_mysteel_reports(html):
    """Return up to five dated titles and links, newest first."""
    soup = BeautifulSoup(html, "html.parser", from_encoding="utf-8")
    reports = {}
    for date_element in soup.select("li > span.date"):
        link = date_element.find_next_sibling("a", href=True)
        if link is None:
            continue
        title = link.get_text(strip=True)
        if not REPORT_TITLE.fullmatch(title):
            continue
        try:
            url = urlsplit(urljoin(MYSTEEL_REPORTS_URL, link["href"]))
            date = datetime.strptime(date_element.get_text(strip=True), "%Y-%m-%d %H:%M")
        except ValueError:
            continue
        match = ARTICLE_PATH.fullmatch(url.path)
        if url.scheme != "https" or url.netloc != "haiyun.mysteel.com" or not match:
            continue
        if url.query or url.fragment or match.group(1) != date.strftime("%y%m%d"):
            continue
        if title != f"{date.month}月{date.day}日国际干散货航运市场日报":
            continue
        canonical_url = url.geturl()
        reports[canonical_url] = {
            "title": title,
            "url": canonical_url,
            "published_at": date.replace(tzinfo=BEIJING_TIME).isoformat(timespec="minutes"),
        }

    return sorted(reports.values(), key=lambda report: report["published_at"], reverse=True)[:5]


def _read_public_html(url):
    try:
        response = requests.get(url, headers=REQUEST_HEADERS, timeout=(5, 8), allow_redirects=False)
    except requests.RequestException as exc:
        raise MysteelReportError(f"Mysteel page could not be reached ({type(exc).__name__}).") from exc

    if response.status_code != 200:
        raise MysteelReportError(f"Mysteel page returned HTTP {response.status_code}.")
    return response.content


def get_mysteel_reports():
    """Fetch the public index without following redirects."""
    reports = parse_mysteel_reports(_read_public_html(MYSTEEL_REPORTS_URL))
    if not reports:
        raise MysteelReportError("Mysteel report index contained no valid dated dry-bulk reports.")
    return reports


def _route_fact(code, clause):
    # Ignore ranges rather than presenting an endpoint as an observed price.
    if re.search(r"\d\s*(?:[-~—–]|至|到)\s*\d", clause):
        return None
    value = None
    change = None
    unit = None
    change_unit = None
    for amount in AMOUNT_PATTERN.finditer(clause):
        number = float(amount["number"].replace(",", "").replace(" ", ""))
        amount_unit = amount["unit"]
        direction = amount["direction"]
        if direction or amount["number"].startswith(("+", "-")):
            if direction:
                number = -abs(number) if direction in {"下跌", "下降", "下调", "跌", "降", "减少"} else abs(number)
            change = number
            change_unit = amount_unit
        elif amount_unit and value is None:
            value = number
            unit = amount_unit
    if value is None and (change is None or not change_unit):
        return None
    if change_unit and unit and change_unit != unit:
        change = None
    if change is None and re.search(r"持平|维持不变", clause):
        change = 0
    if value is not None and re.search(r"成交价|成交(?:在|于|至)?\s*\d", clause):
        kind = "成交价"
    elif value is not None and re.search(r"评估价|估价", clause):
        kind = "评估价"
    else:
        kind = "航线运价"
    return {
        "code": code,
        "label": ROUTES[code][0],
        "value": value,
        "change": change,
        "unit": "美元/吨" if (unit or change_unit) == "吨" else "美元/天",
        "kind": kind,
    }


def _market_signals(clauses):
    signals = []
    for clause in clauses:
        match = re.search(r"国际干散货市场(.{0,25})", clause)
        if match:
            for label, pattern in MARKET_SIGNALS:
                if re.search(pattern, match[1]):
                    signals.append(f"整体市场：{label}")
                    break
            break
    for clause in clauses:
        if re.search(r"澳洲|西澳|黑德兰|C5航线", clause):
            west_australia = []
            if re.search(r"(?:询船|询盘)活跃|需求向好", clause):
                west_australia.append("需求较活跃")
            if re.search(r"运力偏紧|船舶紧张|运力收紧", clause):
                west_australia.append("可用运力偏紧")
            if west_australia:
                signals.append(f"西澳航线：{'，'.join(west_australia)}")
        if re.search(r"巴西航线平稳|(?:巴西|C3).*?航线持稳", clause):
            signals.append("巴西航线：报价整体稳定")
        if "巴拿马型船" in clause:
            if re.search(r"太平洋.*?(?:回落|下跌|走软)", clause):
                signals.append("巴拿马型船：太平洋租运市场走弱")
            elif re.search(r"走软|下跌|回落|弱势", clause):
                signals.append("巴拿马型船：运价偏弱")
            elif re.search(r"上涨|走强|上扬", clause):
                signals.append("巴拿马型船：运价上行")
    return list(dict.fromkeys(signals))[:4]


def parse_mysteel_report_details(html, title):
    """Extract facts from the public description; never collect the article image."""
    soup = BeautifulSoup(html, "html.parser", from_encoding="utf-8")
    heading = soup.select_one("h1#content-title")
    description = soup.select_one('meta[name="description"]')
    if not heading or heading.get_text(strip=True) != title or not description:
        raise MysteelReportError("Mysteel article did not contain its expected public heading and description.")
    overview = normalize("NFKC", description.get("content", "").strip())
    if not overview:
        raise MysteelReportError("Mysteel article public description was empty.")
    clauses = re.split(r"[。;!?]|\.(?!\d)", overview)
    facts = {}
    for clause in clauses:
        routes = list(ROUTE_PATTERN.finditer(clause))
        for index, route in enumerate(routes):
            end = routes[index + 1].start() if index + 1 < len(routes) else len(clause)
            code = route.lastgroup
            fact = _route_fact(code, clause[route.end():end])
            if fact and (code not in facts or facts[code]["value"] is None):
                facts[code] = fact
    return {"facts": list(facts.values()), "summary": _market_signals(clauses)}


def get_mysteel_report_details(report):
    """Read only an article already identified on the official public index."""
    url = urlsplit(report["url"])
    if url.scheme != "https" or url.netloc != "haiyun.mysteel.com" or url.query or url.fragment or not ARTICLE_PATH.fullmatch(url.path):
        raise MysteelReportError("Unrecognized Mysteel article URL.")
    return parse_mysteel_report_details(_read_public_html(report["url"]), report["title"])
