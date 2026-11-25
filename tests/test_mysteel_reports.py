import json
import tempfile
import unittest
from html import escape
from pathlib import Path
from unittest.mock import Mock, patch

import requests

from data.mysteel_reports import (
    MYSTEEL_REPORTS_URL,
    MysteelReportError,
    get_mysteel_report_details,
    get_mysteel_reports,
    parse_mysteel_report_details,
    parse_mysteel_reports,
)
from scripts import sync_mysteel_reports


def article_row(date, url, title):
    return f'<li><span class="date">{date}</span><a href="{url}">{title}</a></li>'


NEWEST_URL = "https://haiyun.mysteel.com/a/26112417/BF77CFF22BBFA5AC.html"
NEWEST_TITLE = "11月24日国际干散货航运市场日报"
NEWEST_ROW = article_row("2026-11-24 17:32", NEWEST_URL, NEWEST_TITLE)


def report_page(description, title=NEWEST_TITLE):
    return (
        f'<meta name="description" content="{escape(description)}">'
        f'<h1 id="content-title">{escape(title)}</h1>'
        '<div id="article-content"><img src="https://example.com/full-report.png" /></div>'
    ).encode("utf-8")


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

    def test_does_not_conflate_fixture_price_and_published_change(self):
        overview = "国际干散货市场稳中走强。西澳询船活跃，运力偏紧，C5成交价15.8美元/吨；C3航线涨0.2美元/吨至34.4美元/吨。"
        data = parse_mysteel_report_details(report_page(overview), NEWEST_TITLE)
        c5, c3 = data["facts"]
        self.assertEqual((c5["code"], c5["kind"], c5["value"], c5["change"]), ("C5", "成交价", 15.8, None))
        self.assertEqual((c3["code"], c3["kind"], c3["value"], c3["change"]), ("C3", "航线运价", 34.4, 0.2))
        self.assertEqual(c3["unit"], "美元/吨")
        self.assertNotIn(overview, repr(data))
        self.assertIn("整体市场：市场偏强", data["summary"])

    def test_handles_route_name_aliases_negative_and_change_only(self):
        overview = "黑德兰至青岛航线跌0.75美元/吨至14.35美元/吨，图巴朗到青岛航线下跌0.08美元/吨；MP11报25.20美元/吨，涨0.3美元。"
        details = parse_mysteel_report_details(report_page(overview), NEWEST_TITLE)
        c5, c3, mp11 = details["facts"]
        self.assertEqual((c5["code"], c5["value"], c5["change"]), ("C5", 14.35, -0.75))
        self.assertEqual((c3["code"], c3["value"], c3["change"]), ("C3", None, -0.08))
        self.assertEqual((mp11["code"], mp11["value"], mp11["change"]), ("MP11", 25.20, 0.3))

    def test_excludes_range_and_does_not_infer_flat_change(self):
        overview = "C5询报价16至16.5美元/吨；C3报35美元/吨，表现平稳。"
        details = parse_mysteel_report_details(report_page(overview), NEWEST_TITLE)
        self.assertEqual(len(details["facts"]), 1)
        self.assertEqual(details["facts"][0]["code"], "C3")
        self.assertIsNone(details["facts"][0]["change"])

    @patch("data.mysteel_reports.requests.get")
    def test_detail_fetch_only_contacts_valid_article_and_checks_heading(self, request):
        report = {"title": NEWEST_TITLE, "url": NEWEST_URL}
        request.return_value = Mock(status_code=200, content=report_page("C5报14.35美元/吨。"))
        self.assertEqual(get_mysteel_report_details(report)["facts"][0]["value"], 14.35)
        request.assert_called_once()
        self.assertEqual(request.call_args.args[0], NEWEST_URL)
        self.assertFalse(request.call_args.kwargs["allow_redirects"])

        with self.assertRaisesRegex(MysteelReportError, "Unrecognized"):
            get_mysteel_report_details({**report, "url": NEWEST_URL + "?download=1"})
        request.assert_called_once()

        with self.assertRaisesRegex(MysteelReportError, "public heading"):
            parse_mysteel_report_details(report_page("C5报14.35美元/吨。", "other"), NEWEST_TITLE)

    @patch("scripts.sync_mysteel_reports.get_mysteel_reports")
    @patch("scripts.sync_mysteel_reports.get_mysteel_report_details")
    def test_sync_preserves_article_facts_when_source_temporarily_fails(self, details, index):
        report = parse_mysteel_reports(NEWEST_ROW.encode("utf-8"))[0]
        index.return_value = [report.copy()]
        details.side_effect = MysteelReportError("timeout")
        with tempfile.TemporaryDirectory() as tmp:
            snapshot = Path(tmp) / "snapshot.json"
            cached = {**report, "facts": [{"code": "C5", "value": 14.35}], "summary": ["运价上涨"]}
            snapshot.write_text(json.dumps({"checked_at": None, "reports": [cached]}), encoding="utf-8")
            with patch.object(sync_mysteel_reports, "SNAPSHOT", snapshot):
                sync_mysteel_reports.sync_reports(force=True)
            result = json.loads(snapshot.read_text(encoding="utf-8"))
            self.assertEqual(result["reports"][0], cached)
