from __future__ import annotations

import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from html import unescape
from typing import Iterable
from urllib.parse import urlparse
import xml.etree.ElementTree as ET

import requests
from bs4 import BeautifulSoup

from .config import DOMAIN_TO_SOURCE, GDELT_URL, SHIPPING_KEYWORDS, SOURCE_WHITELIST, USER_AGENT


UTC = timezone.utc


@dataclass
class Article:
    id: str
    source: str
    source_domain: str
    title: str
    url: str
    published_at: str
    summary: str
    keyword_hint: str
    metadata: dict = field(default_factory=dict)

    def to_prompt_dict(self) -> dict:
        return {
            "id": self.id,
            "source": self.source,
            "title": self.title,
            "url": self.url,
            "published_at": self.published_at,
            "summary": self.summary,
            "keyword_hint": self.keyword_hint,
        }


def _clean_text(value: str) -> str:
    text = unescape(value or "")
    return re.sub(r"\s+", " ", text).strip()


def _normalize_domain(value: str) -> str:
    host = urlparse(value).netloc.lower()
    return host[4:] if host.startswith("www.") else host


def _match_whitelisted_source(url: str) -> tuple[str, str] | None:
    domain = _normalize_domain(url)
    for candidate, source_name in DOMAIN_TO_SOURCE.items():
        if domain == candidate or domain.endswith(f".{candidate}"):
            return source_name, domain
    return None


def _parse_published(value: str) -> datetime | None:
    if not value:
        return None
    for parser in (
        lambda raw: datetime.strptime(raw, "%Y%m%dT%H%M%SZ").replace(tzinfo=UTC),
        lambda raw: datetime.fromisoformat(raw.replace("Z", "+00:00")),
        parsedate_to_datetime,
    ):
        try:
            parsed = parser(value)
            if parsed.tzinfo is None:
                return parsed.replace(tzinfo=UTC)
            return parsed.astimezone(UTC)
        except Exception:
            continue
    return None


class ShippingNewsCollector:
    def __init__(self, session: requests.Session | None = None) -> None:
        self.session = session or requests.Session()
        self.session.headers.update({"User-Agent": USER_AGENT})

    def collect(self, hours: int = 24, target_count: int = 18) -> list[Article]:
        articles: list[Article] = []
        keywords = SHIPPING_KEYWORDS[:]
        if hours > 24:
            keywords.extend(
                [
                    "vessel attack",
                    "port disruption",
                    "shipping market",
                    "energy shipping",
                ]
            )

        with ThreadPoolExecutor(max_workers=4) as executor:
            gdelt_jobs = {
                executor.submit(self._safe_search_gdelt, keyword=keyword, hours=hours, max_records=12): keyword
                for keyword in keywords
            }
            gdelt_results: dict[str, list[Article]] = {}
            for future in as_completed(gdelt_jobs):
                keyword = gdelt_jobs[future]
                gdelt_results[keyword] = future.result()

            for keyword in keywords:
                articles.extend(gdelt_results.get(keyword, []))

            deduped = self._dedupe_articles(articles)
            if len(deduped) >= target_count:
                return self._sort_recent(deduped)[:target_count]

            rss_keywords = [keyword for keyword in keywords if len(gdelt_results.get(keyword, [])) < 3]
            rss_jobs = {
                executor.submit(self._search_google_rss, keyword=keyword, hours=hours, max_records=8): keyword
                for keyword in rss_keywords
            }
            for future in as_completed(rss_jobs):
                articles.extend(future.result())
        deduped = self._dedupe_articles(articles)
        if len(deduped) < target_count and hours <= 24:
            extra = self.collect(hours=48, target_count=target_count)
            deduped = self._dedupe_articles([*deduped, *extra])
        return self._sort_recent(deduped)[: max(target_count, 12)]

    def _safe_search_gdelt(self, keyword: str, hours: int, max_records: int) -> list[Article]:
        try:
            return self._search_gdelt(keyword=keyword, hours=hours, max_records=max_records)
        except Exception:
            return []

    def _search_gdelt(self, keyword: str, hours: int, max_records: int) -> list[Article]:
        domain_filters = " OR ".join(f"domainis:{domain}" for domain in DOMAIN_TO_SOURCE)
        params = {
            "query": f"({domain_filters}) AND {keyword} AND sourcelang:english",
            "mode": "ArtList",
            "format": "json",
            "sort": "DateDesc",
            "maxrecords": str(max_records),
            "timespan": f"{hours}h",
        }
        response = self.session.get(GDELT_URL, params=params, timeout=30)
        response.raise_for_status()
        records = response.json().get("articles", [])
        articles: list[Article] = []
        for index, record in enumerate(records):
            url = str(record.get("url", "")).strip()
            matched = _match_whitelisted_source(url)
            if not matched:
                continue
            source_name, domain = matched
            title = _clean_text(record.get("title", ""))
            published = self._extract_published(record)
            summary = _clean_text(str(record.get("snippet", "") or ""))
            articles.append(
                Article(
                    id=f"{keyword[:12].replace(' ', '_')}_{index}",
                    source=source_name,
                    source_domain=domain,
                    title=title,
                    url=url,
                    published_at=published,
                    summary=summary,
                    keyword_hint=keyword,
                    metadata={"domain": domain},
                )
            )
        return articles

    def _search_google_rss(self, keyword: str, hours: int, max_records: int) -> list[Article]:
        days = 1 if hours <= 24 else 2
        params = {
            "q": f"({keyword}) (shipping OR maritime OR tanker OR port OR bulk OR container) when:{days}d",
            "hl": "en-US",
            "gl": "US",
            "ceid": "US:en",
        }
        response = self.session.get("https://news.google.com/rss/search", params=params, timeout=30)
        response.raise_for_status()
        root = ET.fromstring(response.content)
        articles: list[Article] = []
        source_names = {name.lower(): name for name in SOURCE_WHITELIST}
        for index, item in enumerate(root.findall("./channel/item")):
            source_raw = _clean_text(item.findtext("source", default=""))
            source_name = source_names.get(source_raw.lower())
            if not source_name:
                continue
            title = _clean_text(item.findtext("title", default=""))
            if " - " in title:
                title = title.rsplit(" - ", 1)[0].strip()
            link = _clean_text(item.findtext("link", default=""))
            pub_date = _clean_text(item.findtext("pubDate", default=""))
            description_html = item.findtext("description", default="")
            description = _clean_text(BeautifulSoup(description_html, "html.parser").get_text(" ", strip=True))
            articles.append(
                Article(
                    id=f"rss_{keyword[:12].replace(' ', '_')}_{index}",
                    source=source_name,
                    source_domain="google-news",
                    title=title,
                    url=link,
                    published_at=_parse_published(pub_date).isoformat() if _parse_published(pub_date) else "",
                    summary=description,
                    keyword_hint=keyword,
                    metadata={"fallback": "google_rss"},
                )
            )
            if len(articles) >= max_records:
                break
        return articles

    @staticmethod
    def _canonical_title(title: str) -> str:
        normalized = _clean_text(title).lower()
        normalized = re.sub(r"[^a-z0-9\s]+", " ", normalized)
        return re.sub(r"\s+", " ", normalized).strip()

    @classmethod
    def _dedupe_articles(cls, articles: Iterable[Article]) -> list[Article]:
        deduped: list[Article] = []
        seen_urls: set[str] = set()
        seen_titles: set[str] = set()
        for article in cls._sort_recent(articles):
            canonical_title = cls._canonical_title(article.title)
            if article.url in seen_urls:
                continue
            if canonical_title and canonical_title in seen_titles:
                continue
            seen_urls.add(article.url)
            if canonical_title:
                seen_titles.add(canonical_title)
            deduped.append(article)
        return deduped

    def _fetch_article_summary(self, url: str) -> dict:
        try:
            response = self.session.get(url, timeout=20, allow_redirects=True)
            response.raise_for_status()
        except Exception:
            return {}
        soup = BeautifulSoup(response.text, "html.parser")
        title = (
            self._meta_content(soup, "property", "og:title")
            or self._meta_content(soup, "name", "twitter:title")
            or (soup.title.get_text(" ", strip=True) if soup.title else "")
        )
        summary = (
            self._meta_content(soup, "name", "description")
            or self._meta_content(soup, "property", "og:description")
            or self._meta_content(soup, "name", "twitter:description")
        )
        published_raw = (
            self._meta_content(soup, "property", "article:published_time")
            or self._meta_content(soup, "name", "pubdate")
            or self._meta_content(soup, "name", "publish-date")
            or self._meta_content(soup, "itemprop", "datePublished")
            or self._find_time_datetime(soup)
        )
        published = _parse_published(published_raw)
        return {
            "title": _clean_text(title),
            "summary": _clean_text(summary),
            "published_at": published.isoformat() if published else "",
        }

    @staticmethod
    def _meta_content(soup: BeautifulSoup, attr_name: str, attr_value: str) -> str:
        node = soup.find("meta", attrs={attr_name: attr_value})
        return str(node.get("content", "")) if node else ""

    @staticmethod
    def _find_time_datetime(soup: BeautifulSoup) -> str:
        time_node = soup.find("time")
        return str(time_node.get("datetime", "")).strip() if time_node else ""

    @staticmethod
    def _extract_published(record: dict) -> str:
        for candidate in (record.get("seendate"), record.get("socialimage:published"), record.get("date")):
            parsed = _parse_published(str(candidate or ""))
            if parsed:
                return parsed.isoformat()
        return ""

    @staticmethod
    def _sort_recent(articles: Iterable[Article]) -> list[Article]:
        now = datetime.now(UTC)

        def sort_key(article: Article) -> datetime:
            parsed = _parse_published(article.published_at)
            return parsed or (now - timedelta(days=365))

        return sorted(articles, key=sort_key, reverse=True)
