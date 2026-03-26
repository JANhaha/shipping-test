import hashlib
import json
import re
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

import requests
from bs4 import BeautifulSoup


class ShippingDashboardService:
    CACHE_TTL_SECONDS = 1800
    HIFLEET_URL = "https://www.hifleet.com/shipping/"
    BOC_URL = "https://www.boc.cn/sourcedb/whpj/"
    BUNKER_INDEX_URL = "https://www.bunkerindex.com/"
    ZHOUSHAN_API_URL = "https://www.hyqfocus.com/app/findBunkerPriceListByPortId"
    HIFLEET_BALTIC_HISTORY_API = "https://www.hifleet.com/shipdetail/getBalticexchange"
    HIFLEET_BALTIC_TABLE_API = "https://www.hifleet.com/shipdetail/getBalticexchangeToTable"
    MYSTEEL_APP_KEY = "47EE3F12CF0C443F8FD51EFDA73AC815"
    MYSTEEL_APP_SECRET = "3BA6477330684B19AA6AF4485497B5F2"

    def __init__(self):
        self.session = requests.Session()
        self.session.trust_env = False
        self.session.headers.update(
            {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0 Safari/537.36"
                )
            }
        )
        self.cache = {}

    def get_dashboard(self):
        return self._cached("dashboard", self._load_dashboard)

    def _load_dashboard(self):
        with ThreadPoolExecutor(max_workers=8) as executor:
            futures = {
                "baltic": executor.submit(self._call_safe, self.get_baltic_indices, "Baltic Exchange"),
                "iron_ore": executor.submit(self._call_safe, self.get_iron_ore_index, "进口矿指数"),
                "boc_usd": executor.submit(self._call_safe, self.get_boc_usd_rate, "中行美元折算价"),
                "bunker_index": executor.submit(self._call_safe, self.get_bunker_prices, "Bunker Index"),
                "zhoushan": executor.submit(self._call_safe, self.get_zhoushan_bunker, "舟山油价"),
                "cl": executor.submit(
                    self._call_safe,
                    self.get_market_series,
                    "CL",
                    name="NYMEX WTI (CL)",
                    yahoo_symbol="CL=F",
                    source_url="https://finance.sina.com.cn/futures/quotes/CL.shtml?id=27",
                ),
                "oil": executor.submit(
                    self._call_safe,
                    self.get_market_series,
                    "OIL",
                    name="Brent (OIL)",
                    yahoo_symbol="BZ=F",
                    source_url="https://finance.sina.com.cn/futures/quotes/OIL.shtml",
                ),
                "DINIW": executor.submit(
                    self._call_safe,
                    self.get_forex_series,
                    "DINIW",
                    code="DINIW",
                    title="美元指数",
                    yahoo_symbol="DX-Y.NYB",
                    quote_symbol="DINIW",
                    source_url="https://finance.sina.com.cn/money/forex/hq/DINIW.shtml",
                ),
                "EURCNY": executor.submit(
                    self._call_safe,
                    self.get_forex_series,
                    "EURCNY",
                    code="EURCNY",
                    title="欧元兑人民币",
                    yahoo_symbol="EURCNY=X",
                    quote_symbol="EURCNY",
                    source_url="https://finance.sina.com.cn/money/forex/hq/EURCNY.shtml",
                ),
                "GBPUSD": executor.submit(
                    self._call_safe,
                    self.get_forex_series,
                    "GBPUSD",
                    code="GBPUSD",
                    title="英镑兑美元",
                    yahoo_symbol="GBPUSD=X",
                    quote_symbol="GBPUSD",
                    source_url="https://finance.sina.com.cn/money/forex/hq/GBPUSD.shtml",
                ),
                "USDCNY": executor.submit(
                    self._call_safe,
                    self.get_forex_series,
                    "USDCNY",
                    code="USDCNY",
                    title="美元兑人民币",
                    yahoo_symbol="USDCNY=X",
                    quote_symbol="USDCNY",
                    source_url="https://finance.sina.com.cn/money/forex/hq/USDCNY.shtml",
                ),
                "USDHKD": executor.submit(
                    self._call_safe,
                    self.get_forex_series,
                    "USDHKD",
                    code="USDHKD",
                    title="美元兑港元",
                    yahoo_symbol="USDHKD=X",
                    quote_symbol="USDHKD",
                    source_url="https://finance.sina.com.cn/money/forex/hq/USDHKD.shtml",
                ),
                "USDJPY": executor.submit(
                    self._call_safe,
                    self.get_forex_series,
                    "USDJPY",
                    code="USDJPY",
                    title="美元兑日元",
                    yahoo_symbol="USDJPY=X",
                    quote_symbol="USDJPY",
                    source_url="https://finance.sina.com.cn/money/forex/hq/USDJPY.shtml",
                ),
            }

        return {
            "timestamp": datetime.now().isoformat(),
            "refresh_interval_minutes": 30,
            "baltic": futures["baltic"].result(),
            "crude": {"cl": futures["cl"].result(), "oil": futures["oil"].result()},
            "iron_ore": futures["iron_ore"].result(),
            "boc_usd": futures["boc_usd"].result(),
            "forex": {
                "DINIW": futures["DINIW"].result(),
                "EURCNY": futures["EURCNY"].result(),
                "GBPUSD": futures["GBPUSD"].result(),
                "USDCNY": futures["USDCNY"].result(),
                "USDHKD": futures["USDHKD"].result(),
                "USDJPY": futures["USDJPY"].result(),
            },
            "bunker_index": futures["bunker_index"].result(),
            "zhoushan": futures["zhoushan"].result(),
        }

    def get_baltic_indices(self):
        payload = {"type": "balticexchange", "identifier": "balticexchange", "i18n": "zh"}
        history_response = self.session.post(
            self.HIFLEET_BALTIC_HISTORY_API,
            data=payload,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=30,
        )
        table_response = self.session.post(
            self.HIFLEET_BALTIC_TABLE_API,
            data=payload,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=30,
        )
        history_data = history_response.json().get("data", {})
        table_rows = table_response.json().get("data", [])
        table_map = {row.get("indexName"): row for row in table_rows}

        names = {
            "BDI": "Baltic Dry Index",
            "BCI": "Baltic Capesize Index",
            "BPI": "Baltic Panamax Index",
            "BSI": "Baltic Supramax Index",
            "BHSI": "Baltic Handysize Index",
            "BCTI": "Baltic Clean Tanker Index",
            "BDTI": "Baltic Dirty Tanker Index",
            "BLNG": "Baltic LNG Index",
            "BLPG": "Baltic LPG Index",
        }
        rows = []
        for code, name in names.items():
            history_rows = history_data.get(code, [])
            latest = history_rows[-1] if history_rows else {}
            table_row = table_map.get(code, {})
            current = table_row.get("current") or latest.get("value")
            daily = self._signed_float(table_row.get("daily"))
            rate_change = self._signed_float(table_row.get("rateOfChange"))
            rows.append(
                {
                    "code": code,
                    "name": name,
                    "value": self._to_float(current),
                    "trend": daily is not None and daily >= 0,
                    "daily_percent": daily,
                    "change": rate_change,
                    "date": (table_row.get("currentTime") or latest.get("indexDate") or "")[:10],
                }
            )

        return {
            "data": rows,
            "error": None if rows else "未能从 HiFleet 解析出 Baltic 指数数据。",
            "source_url": self.HIFLEET_URL,
            "updated_at": datetime.now().isoformat(),
        }

    def get_market_series(self, name, yahoo_symbol, source_url):
        series = self._yahoo_series(yahoo_symbol)
        latest = series[-1]["value"] if series else None
        previous = series[-2]["value"] if len(series) > 1 else None
        change = round(latest - previous, 4) if latest is not None and previous is not None else None
        return {
            "name": name,
            "latest": latest,
            "previous": previous,
            "change": change,
            "series": series,
            "source_url": source_url,
            "chart_source": "Yahoo Finance chart API",
            "updated_at": datetime.now().isoformat(),
        }

    def get_forex_series(self, code, title, yahoo_symbol, quote_symbol, source_url):
        series = self._yahoo_series(yahoo_symbol)
        quote = self._sina_quote(quote_symbol)
        latest = quote.get("current") if quote else (series[-1]["value"] if series else None)
        previous_close = quote.get("previous_close") if quote else None
        return {
            "code": code,
            "title": title,
            "latest": latest,
            "previous_close": previous_close,
            "change": quote.get("change") if quote else None,
            "change_percent": quote.get("change_percent") if quote else None,
            "series": series,
            "source_url": source_url,
            "chart_source": "Yahoo Finance chart API",
            "quote_source": "Sina HQ" if quote else "Yahoo Finance chart API",
            "updated_at": datetime.now().isoformat(),
        }

    def get_iron_ore_index(self):
        rows = self._mysteel_report(
            path="/zs/newxpic/getReport.ms",
            params={
                "tabName": "JINKOUKUANG",
                "typeName": "进口矿",
                "dateType": "day",
                "startTime": "",
                "endTime": "",
                "returnType": "",
            },
        ).get("data", [])
        today = rows[0] if rows else {}
        yesterday = rows[1] if len(rows) > 1 else {}
        return {
            "name": "进口矿指数",
            "today": {"date": today.get("date"), "value": self._to_float(today.get("value"))},
            "yesterday": {"date": yesterday.get("date"), "value": self._to_float(yesterday.get("value"))},
            "change_percent": self._signed_float(today.get("lastDayScale")),
            "source_url": "https://index.mysteel.com/xpic/detail.html?tabName=kuangsi",
            "updated_at": datetime.now().isoformat(),
        }

    def get_boc_usd_rate(self):
        response = self.session.get(self.BOC_URL, timeout=30)
        response.encoding = "utf-8"
        soup = BeautifulSoup(response.text, "html.parser")
        usd_row = None
        for tr in soup.select("table tr"):
            cells = [cell.get_text(" ", strip=True) for cell in tr.select("th,td")]
            if cells and cells[0] == "美元":
                usd_row = cells
                break

        if not usd_row:
            return {
                "error": "未能解析中行美元折算价。",
                "source_url": self.BOC_URL,
                "updated_at": datetime.now().isoformat(),
            }

        return {
            "currency": usd_row[0],
            "spot_buy": self._to_float(usd_row[1]),
            "cash_buy": self._to_float(usd_row[2]),
            "spot_sell": self._to_float(usd_row[3]),
            "cash_sell": self._to_float(usd_row[4]),
            "conversion_price": self._to_float(usd_row[5]),
            "published_at": usd_row[6],
            "published_time": usd_row[7],
            "source_url": self.BOC_URL,
            "updated_at": datetime.now().isoformat(),
        }

    def get_bunker_prices(self):
        html = self._get_text(self.BUNKER_INDEX_URL)
        soup = BeautifulSoup(html, "html.parser")
        table = soup.select_one("#price-table")
        rows = []
        if table:
            for tr in table.select("tr")[1:]:
                cells = [cell.get_text(" ", strip=True) for cell in tr.select("th,td")]
                if len(cells) != 9:
                    continue
                visible_prices = [cells[2], cells[4], cells[6]]
                if not any(self._is_visible_price(value) for value in visible_prices):
                    continue
                rows.append(
                    {
                        "port": cells[0],
                        "country": cells[1],
                        "ifo380": cells[2],
                        "ifo380_change": cells[3],
                        "vlsfo": cells[4],
                        "vlsfo_change": cells[5],
                        "mgo": cells[6],
                        "mgo_change": cells[7],
                        "date": cells[8],
                    }
                )
        return {
            "ports": rows,
            "source_url": self.BUNKER_INDEX_URL,
            "updated_at": datetime.now().isoformat(),
        }

    def get_zhoushan_bunker(self):
        response = self.session.get(
            self.ZHOUSHAN_API_URL,
            params={"portId": 177, "max": 30},
            timeout=30,
        )
        rows = response.json()
        latest = rows[0] if rows else {}
        return {
            "port": latest.get("portName", "Zhoushan"),
            "date": self._format_millis(latest.get("updateDate")),
            "prices": {
                "IFO380": latest.get("ifo380"),
                "LSMGO": latest.get("lsmgo"),
                "VLSFO": latest.get("vlsfo"),
            },
            "source_url": "https://www.zsbunker.cn/bunker_zhoushan.jsp",
            "updated_at": datetime.now().isoformat(),
        }

    def _cached(self, key, loader):
        now = time.time()
        cached = self.cache.get(key)
        if cached and now - cached[0] < self.CACHE_TTL_SECONDS:
            return cached[1]
        value = loader()
        self.cache[key] = (now, value)
        return value

    def _get_text(self, url):
        response = self.session.get(url, timeout=30)
        if "boc.cn" in url:
            response.encoding = "utf-8"
        else:
            response.encoding = response.apparent_encoding or "utf-8"
        return response.text

    def _yahoo_series(self, symbol):
        response = self.session.get(
            f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}",
            params={"range": "10d", "interval": "1d", "includePrePost": "false"},
            timeout=30,
        )
        payload = response.json()
        result = payload["chart"]["result"][0]
        timestamps = result.get("timestamp") or []
        closes = result.get("indicators", {}).get("quote", [{}])[0].get("close") or []
        rows = []
        for stamp, close in zip(timestamps, closes):
            if close is None:
                continue
            rows.append(
                {
                    "date": datetime.utcfromtimestamp(stamp).strftime("%m-%d"),
                    "value": round(float(close), 4),
                }
            )
        return rows[-5:]

    def _sina_quote(self, code):
        symbol = "DINIW" if code == "DINIW" else f"fx_s{code.lower()}"
        response = self.session.get(
            "https://hq.sinajs.cn/",
            params={"list": symbol},
            headers={"Referer": "https://finance.sina.com.cn/"},
            timeout=20,
        )
        response.encoding = "gbk"
        text = response.text
        if '=""' in text:
            return None
        raw = text.split('="', 1)[-1].rsplit('";', 1)[0]
        parts = raw.split(",")
        if len(parts) < 9:
            return None
        current = self._to_float(parts[8])
        previous_close = self._to_float(parts[1])
        change = None
        change_percent = None
        if current is not None and previous_close not in (None, 0):
            change = round(current - previous_close, 4)
            change_percent = round(change / previous_close * 100, 4)
        return {
            "current": current,
            "previous_close": previous_close,
            "change": change,
            "change_percent": change_percent,
        }

    def _mysteel_report(self, path, params):
        timestamp = str(int(time.time() * 1000))
        source = f"path{path}timestamp{timestamp}version1.0.0{self.MYSTEEL_APP_SECRET}"
        sign = hashlib.md5(source.encode("utf-8")).hexdigest().upper()
        response = self.session.get(
            f"https://index.mysteel.com{path}",
            params={**params, "callback": "json", "v": timestamp},
            headers={
                "version": "1.0.0",
                "appKey": self.MYSTEEL_APP_KEY,
                "timestamp": timestamp,
                "sign": sign,
            },
            timeout=30,
        )
        return json.loads(response.text)

    @staticmethod
    def _call_safe(func, label, *args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as exc:
            return {
                "error": f"{label} 抓取失败: {exc}",
                "updated_at": datetime.now().isoformat(),
            }

    @staticmethod
    def _format_millis(value):
        if value in (None, ""):
            return None
        return datetime.fromtimestamp(int(value) / 1000).strftime("%Y-%m-%d")

    @staticmethod
    def _to_float(value):
        if value in (None, "", "--", "Subscribe"):
            return None
        return float(str(value).replace(",", ""))

    @staticmethod
    def _signed_float(value):
        if value in (None, ""):
            return None
        return float(str(value).replace("%", ""))

    @staticmethod
    def _is_visible_price(value):
        return value not in (None, "", "--", "Subscribe")
