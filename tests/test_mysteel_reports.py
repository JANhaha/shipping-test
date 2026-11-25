import unittest
from unittest.mock import Mock, patch

import requests

from data.mysteel_reports import MYSTEEL_REPORTS_URL, MysteelReportError, get_mysteel_reports, parse_mysteel_reports


def article_row(date, url, title):
    return f'<li><span class="date">{date}</span><a href="{url}">{title}</a></li>'


NEWEST_URL = "https://haiyun.mysteel.com/a/26112417/BF77CFF22BBFA5AC.html"
NEWEST_TITLE = "11月24日国际干散货航运市场日报"
NEWEST_ROW = article_row("2026-11-24 17:32", NEWEST_URL, NEWEST_TITLE)


class MysteelReportsTest(unittest.TestCase):
    def test_filters_untrusted_and_unrelated_links_and_sorts_by_source_time(self):
        html = "<ul>" + "".join([
            article_row("2026-11-23 17:30", "/a/26112317/54EDAEA5186E0D32.html", "11月23日国际干散货航运市场日报"),
            article_row("2026-11-24 17:32", NEWEST_URL.replace("haiyun.mysteel.com", "haiyun.mysteel.com.example"), NEWEST_TITLE),
            article_row("2026-11-24 17:32", NEWEST_URL.replace("https:", "http:"), NEWEST_TITLE),
            article_row("2026-11-24 17:32", NEWEST_URL + "?tracking=1", NEWEST_TITLE),
            article_row("2026-11-24 17:32", NEWEST_URL.replace("/a/", "/oilchem/a/"), NEWEST_TITLE),
            article_row("2026-11-24 17:32", NEWEST_URL, "国际干散货航运市场周报"),
            article_row("2026-11-31 17:32", NEWEST_URL, NEWEST_TITLE),
            article_row("2026-11-25 17:32", NEWEST_URL, NEWEST_TITLE),
            article_row("2026-11-24 17:32", NEWEST_URL, "11月25日国际干散货航运市场日报"),
            NEWEST_ROW,
            NEWEST_ROW,
        ]) + "</ul>"
        reports = parse_mysteel_reports(html.encode("utf-8"))
        self.assertEqual(len(reports), 2)
        self.assertEqual(reports[0], {
            "title": NEWEST_TITLE,
            "url": NEWEST_URL,
            "published_at": "2026-11-24T17:32+08:00",
        })
        self.assertEqual(reports[1]["published_at"], "2026-11-23T17:30+08:00")

    @patch("data.mysteel_reports.requests.get")
    def test_fetch_returns_metadata_only(self, request):
        request.return_value = Mock(status_code=200, content=NEWEST_ROW.encode("utf-8"))
        self.assertEqual(get_mysteel_reports()[0]["url"], NEWEST_URL)
        self.assertEqual(request.call_args.args[0], MYSTEEL_REPORTS_URL)
        self.assertFalse(request.call_args.kwargs["allow_redirects"])

    @patch("data.mysteel_reports.requests.get")
    def test_fetch_surfaces_upstream_failures_for_cached_fallback(self, request):
        request.return_value = Mock(status_code=403)
        with self.assertRaisesRegex(MysteelReportError, "HTTP 403"):
            get_mysteel_reports()

        request.return_value = Mock(status_code=200, content=b"<html>no report</html>")
        with self.assertRaisesRegex(MysteelReportError, "no valid dated"):
            get_mysteel_reports()

        request.side_effect = requests.Timeout
        with self.assertRaisesRegex(MysteelReportError, "Timeout"):
            get_mysteel_reports()
