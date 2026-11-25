"""Read article metadata from Mysteel's public shipping report index."""

import re
from datetime import datetime, timedelta, timezone
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


def get_mysteel_reports():
    """Fetch the public index without following redirects or loading articles."""
    try:
        response = requests.get(MYSTEEL_REPORTS_URL, headers=REQUEST_HEADERS, timeout=(5, 8), allow_redirects=False)
    except requests.RequestException as exc:
        raise MysteelReportError(f"Mysteel report index could not be reached ({type(exc).__name__}).") from exc

    if response.status_code != 200:
        raise MysteelReportError(f"Mysteel report index returned HTTP {response.status_code}.")
    reports = parse_mysteel_reports(response.content)
    if not reports:
        raise MysteelReportError("Mysteel report index contained no valid dated dry-bulk reports.")
    return reports
