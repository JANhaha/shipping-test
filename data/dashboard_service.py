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
    HIFLEET_BALTIC_HISTORY_API = "https://www.hifleet.com/shipdetail/getBalticexchange"
    HIFLEET_BALTIC_TABLE_API = "https://www.hifleet.com/shipdetail/getBalticexchangeToTable"
    BOC_URL = "https://www.boc.cn/sourcedb/whpj/"
    BUNKER_INDEX_URL = "https://www.bunkerindex.com/"
    ZHOUSHAN_API_URL = "https://www.hyqfocus.com/app/findBunkerPriceListByPortId"
    CBFI_URL = "https://www.sse.net.cn/index/singleIndex?indexType=cbfi"
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
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = {
                "shipping_indices": executor.submit(self._call_safe, self.get_baltic_indices, "航运相关指数"),
                "cbfi": executor.submit(self._call_safe, self.get_cbfi_index, "中国沿海散货运价指数"),
                "iron_ore": executor.submit(self._call_safe, self.get_iron_ore_index, "进口矿指数"),
                "boc_usd": executor.submit(self._call_safe, self.get_boc_usd_rate, "中行美元折算价"),
                "bunker_index": executor.submit(self._call_safe, self.get_bunker_prices, "全球主要港口油价"),
                "wti": executor.submit(
                    self._call_safe,
                    self.get_crude_quote,
                    "WTI原油",
                    "CL",
                    "WTI原油",
                    "https://finance.sina.com.cn/futures/quotes/CL.shtml?id=27",
                ),
                "brent": executor.submit(
                    self._call_safe,
                    self.get_crude_quote,
                    "布伦特原油CFD",
                    "OIL",
                    "布伦特原油CFD",
                    "https://finance.sina.com.cn/futures/quotes/OIL.shtml",
                ),
                "DINIW": executor.submit(
                    self._call_safe,
                    self.get_forex_quote,
                    "美元指数",
                    "DINIW",
                    "美元指数",
                    "https://finance.sina.com.cn/money/forex/hq/DINIW.shtml",
                ),
                "EURUSD": executor.submit(
                    self._call_safe,
                    self.get_forex_quote,
                    "欧元兑美元",
                    "EURUSD",
                    "欧元兑美元",
                    "https://finance.sina.com.cn/money/forex/hq/EURUSD.shtml",
                ),
                "GBPUSD": executor.submit(
                    self._call_safe,
                    self.get_forex_quote,
                    "英镑兑美元",
                    "GBPUSD",
                    "英镑兑美元",
                    "https://finance.sina.com.cn/money/forex/hq/GBPUSD.shtml",
                ),
                "USDCNY": executor.submit(
                    self._call_safe,
                    self.get_forex_quote,
                    "美元兑人民币",
                    "USDCNY",
                    "美元兑人民币",
                    "https://finance.sina.com.cn/money/forex/hq/USDCNY.shtml",
                ),
                "USDHKD": executor.submit(
                    self._call_safe,
                    self.get_forex_quote,
                    "美元兑港元",
                    "USDHKD",
                    "美元兑港元",
                    "https://finance.sina.com.cn/money/forex/hq/USDHKD.shtml",
                ),
                "USDJPY": executor.submit(
                    self._call_safe,
                    self.get_forex_quote,
                    "美元兑日元",
                    "USDJPY",
                    "美元兑日元",
                    "https://finance.sina.com.cn/money/forex/hq/USDJPY.shtml",
                ),
            }

        return {
            "timestamp": datetime.now().isoformat(),
            "refresh_interval_minutes": 30,
            "baltic": futures["shipping_indices"].result(),
            "cbfi": futures["cbfi"].result(),
            "crude": {
                "cl": futures["wti"].result(),
                "oil": futures["brent"].result(),
            },
            "iron_ore": futures["iron_ore"].result(),
            "boc_usd": futures["boc_usd"].result(),
            "forex": {
                "DINIW": futures["DINIW"].result(),
                "EURUSD": futures["EURUSD"].result(),
                "GBPUSD": futures["GBPUSD"].result(),
                "USDCNY": futures["USDCNY"].result(),
                "USDHKD": futures["USDHKD"].result(),
                "USDJPY": futures["USDJPY"].result(),
            },
            "bunker_index": futures["bunker_index"].result(),
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
            "BDI": "波罗的海干散货指数",
            "BCI": "海岬型船指数",
            "BPI": "巴拿马型船指数",
            "BSI": "超灵便型船指数",
            "BHSI": "灵便型船指数",
            "BCTI": "成品油轮指数",
            "BDTI": "原油轮指数",
            "BLNG": "LNG指数",
            "BLPG": "LPG指数",
        }
        rows = []
        for code, name in names.items():
            history_rows = history_data.get(code, [])
            latest = history_rows[-1] if history_rows else {}
            table_row = table_map.get(code, {})
            current = table_row.get("current") or latest.get("value")
            rows.append(
                {
                    "code": code,
                    "name": name,
                    "value": self._to_float(current),
                    "daily_percent": self._signed_float(table_row.get("daily")),
                    "change": self._signed_float(table_row.get("rateOfChange")),
                    "date": (table_row.get("currentTime") or latest.get("indexDate") or "")[:10],
                }
            )

        return {
            "data": rows,
            "error": None if rows else "未能获取航运相关指数数据。",
            "source_url": self.HIFLEET_URL,
            "updated_at": datetime.now().isoformat(),
        }

    def get_cbfi_index(self):
        response = self.session.get(self.CBFI_URL, timeout=30)
        response.encoding = response.apparent_encoding or "utf-8"
        soup = BeautifulSoup(response.text, "html.parser")
        table = soup.select_one("table.lb1")
        if not table:
            return {
                "error": "未能解析中国沿海散货运价指数页面。",
                "source_url": self.CBFI_URL,
                "updated_at": datetime.now().isoformat(),
            }

        header_cells = [cell.get_text(" ", strip=True) for cell in table.select("tr")[0].select("td,th")]
        previous_date = self._extract_date(header_cells[2] if len(header_cells) > 2 else "")
        current_date = self._extract_date(header_cells[3] if len(header_cells) > 3 else "")

        rows = []
        for tr in table.select("tr")[1:]:
            cells = [cell.get_text(" ", strip=True) for cell in tr.select("td,th")]
            if len(cells) < 5:
                continue
            rows.append(
                {
                    "route": cells[0],
                    "ship_type": cells[1],
                    "previous": self._to_float(cells[2]),
                    "current": self._to_float(cells[3]),
                    "change_percent": self._signed_float(cells[4]),
                }
            )

        overview = next((row for row in rows if row["route"] == "综合指数"), rows[0] if rows else None)
        highlights = [
            row
            for row in rows
            if row["route"] in {"综合指数", "沿海干散货指数", "煤炭货种指数", "粮食货种指数", "金属矿石货种指数", "沿海油品指数"}
        ]
        detail_rows = [row for row in rows if row["ship_type"]]

        return {
            "name": "中国沿海散货运价指数",
            "overview": overview,
            "highlights": highlights,
            "routes": detail_rows,
            "previous_date": previous_date,
            "current_date": current_date,
            "source_url": self.CBFI_URL,
            "updated_at": datetime.now().isoformat(),
        }

    def get_crude_quote(self, code, name, source_url):
        quote = self._sina_global_future_quote(code)
        open_price = quote["open"] if quote else None
        latest = quote["current"] if quote else None
        change_from_open = None
        change_percent_from_open = None
        if latest is not None and open_price not in (None, 0):
            change_from_open = round(latest - open_price, 4)
            change_percent_from_open = round(change_from_open / open_price * 100, 4)
        return {
            "code": code,
            "name": name,
            "latest": latest,
            "open": open_price,
            "previous_close": quote["previous_close"] if quote else None,
            "change_from_open": change_from_open,
            "change_percent_from_open": change_percent_from_open,
            "source_url": source_url,
            "quote_source": "Sina HQ" if quote else None,
            "updated_at": datetime.now().isoformat(),
        }

    def get_forex_quote(self, code, title, source_url):
        quote = self._sina_quote(code)
        open_price = quote.get("open") if quote else None
        latest = quote.get("current") if quote else None
        change_from_open = None
        change_percent_from_open = None
        if latest is not None and open_price not in (None, 0):
            change_from_open = round(latest - open_price, 4)
            change_percent_from_open = round(change_from_open / open_price * 100, 4)
        return {
            "code": code,
            "title": title,
            "latest": latest,
            "open": open_price,
            "previous_close": quote.get("previous_close") if quote else None,
            "change_from_open": change_from_open,
            "change_percent_from_open": change_percent_from_open,
            "source_url": source_url,
            "quote_source": "Sina HQ" if quote else None,
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

        zhoushan = self.get_zhoushan_bunker()
        if zhoushan.get("prices"):
            rows.insert(
                0,
                {
                    "port": zhoushan.get("port") or "Zhoushan",
                    "country": "CN",
                    "ifo380": zhoushan["prices"].get("IFO380"),
                    "ifo380_change": None,
                    "vlsfo": zhoushan["prices"].get("VLSFO"),
                    "vlsfo_change": None,
                    "mgo": zhoushan["prices"].get("LSMGO"),
                    "mgo_change": None,
                    "date": zhoushan.get("date"),
                },
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
            "date": self._format_bunker_date(latest.get("updateDate")),
            "prices": {
                "IFO380": self._to_float(latest.get("ifo380")),
                "LSMGO": self._to_float(latest.get("lsmgo")),
                "VLSFO": self._to_float(latest.get("vlsfo")),
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
        response.encoding = "utf-8" if "boc.cn" in url else (response.apparent_encoding or "utf-8")
        return response.text

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
        if len(parts) < 10:
            return None
        return {
            "current": self._to_float(parts[8]),
            "open": self._to_float(parts[5]),
            "previous_close": self._to_float(parts[3]),
            "date": parts[-1][:10] if parts[-1] else None,
        }

    def _sina_global_future_quote(self, code):
        response = self.session.get(
            "https://hq.sinajs.cn/",
            params={"list": f"hf_{code}"},
            headers={"Referer": "https://finance.sina.com.cn/"},
            timeout=20,
        )
        response.encoding = "gbk"
        text = response.text
        if '=""' in text:
            return None
        raw = text.split('="', 1)[-1].rsplit('";', 1)[0]
        parts = raw.split(",")
        if len(parts) < 14:
            return None
        return {
            "current": self._to_float(parts[0]),
            "open": self._to_float(parts[2]),
            "previous_close": self._to_float(parts[7]),
            "date": parts[12][:10] if len(parts) > 12 and parts[12] else None,
            "name": parts[13] if len(parts) > 13 else code,
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
    def _call_safe(func, label, *args):
        try:
            return func(*args)
        except Exception as exc:
            return {
                "error": f"{label}抓取失败: {exc}",
                "updated_at": datetime.now().isoformat(),
            }

    @staticmethod
    def _extract_date(text):
        match = re.search(r"\d{4}-\d{2}-\d{2}", text or "")
        return match.group(0) if match else None

    @staticmethod
    def _format_bunker_date(value):
        if value in (None, ""):
            return None
        return datetime.fromtimestamp(int(value) / 1000).strftime("%d %b")

    @staticmethod
    def _to_float(value):
        if value in (None, "", "--", "Subscribe"):
            return None
        return float(str(value).replace(",", ""))

    @staticmethod
    def _signed_float(value):
        if value in (None, ""):
            return None
        return float(str(value).replace("%", "").replace(",", ""))

    @staticmethod
    def _is_visible_price(value):
        return value not in (None, "", "--", "Subscribe")
