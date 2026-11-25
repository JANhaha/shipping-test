"""Normalize ship-market observations from the commentary in a Mysteel report."""

import re
from unicodedata import normalize


VESSEL = re.compile(
    r"(?:(?P<capesize>海[岬峡呷帅]?型船?)|"
    r"(?P<panamax>巴拿马型船?|卡姆萨尔型船?)|"
    r"(?P<supramax>超灵便型船?|大灵便型船?|超灵便船)|"
    r"(?P<handysize>灵便型船?|小灵便型船?|灵便船))"
    r"(?:舶|散货船)?(?:的)?市场"
)
MARKET = re.compile(
    r"(?:整体|总体|综合)(?:来)?(?:看|看来|来说)[,，]?"
    r"|(?:今日|当日|今天)国际干散货(?:航运)?市场"
)
REGION = re.compile(
    r"(?P<australia>西澳|澳洲|澳大利亚)(?:航线|市场)"
    r"|(?P<brazil>巴西)(?:航线|市场)"
    r"|(?P<atlantic>大西洋)(?:地区|区域|航线|市场)?"
    r"|(?P<pacific>太平洋)(?:地区|区域|航线|市场)?"
    r"|(?P<india>印度东海岸|印度洋)(?:航线|市场)?"
    r"|(?P<southeast_asia>东南亚)(?:航线|市场)"
)
REGION_LABELS = {
    "australia": "澳洲航线",
    "brazil": "巴西航线",
    "atlantic": "大西洋",
    "pacific": "太平洋",
    "india": "印度洋",
    "southeast_asia": "东南亚",
}

DIRECTIONS = (
    ("走势分化", r"走势不一|分化|涨跌互现"),
    ("小幅上行", r"小幅(?:上行|上涨|回升|上扬|走高)|稳中(?:有升|小涨)"),
    ("小幅回落", r"小幅(?:回落|下跌|下行|走低)|稳中(?:有降|小跌)"),
    ("涨势较强", r"大幅(?:上涨|上行|走高)|明显走强|持续走强"),
    ("跌势较明显", r"大幅(?:下跌|回落|下行)|明显走弱|持续走弱"),
    ("市场偏强", r"稳中(?:向好|走强|偏强)|有所提振|偏强|回暖|好转|走强"),
    ("市场偏弱", r"稳中(?:走弱|偏弱)|低迷|偏弱|走软|疲软|承压|弱势|走弱"),
    ("窄幅波动", r"小幅波动|波动不大|窄幅(?:整理|震荡|波动)|区间震荡"),
    ("持稳", r"平稳|持稳|以稳为主|保持稳定|维持稳定|基本稳定"),
)
DRIVERS = (
    ("询盘增加", r"(?:询船|询盘)(?:明显)?(?:增多|增加|活跃)|询船意愿(?:较强|上升)"),
    ("询盘有限", r"(?:询船|询盘|询报盘)(?:有限|不多|偏少|减少)"),
    ("货盘需求向好", r"(?:需求|拿货意愿)(?:有所|明显)?(?:向好|回升|改善|增加|较好)|货盘增加"),
    ("货盘跟进有限", r"船多货少|货盘不足|需求偏弱|缺乏新货盘|货盘稀少"),
    ("煤炭货盘有支撑", r"煤炭货盘需求(?:尚可|较好|向好)|煤炭货盘(?:增加|活跃)"),
    ("运力供需较均衡", r"供需(?:相对|较为|基本)?均衡|供需平衡"),
    ("可用船舶偏紧", r"(?:运力|可用船舶|可用船只|船舶供给)(?:仍然|继续|相对|较为)?(?:偏紧|紧张|收紧)"),
    ("可用船舶偏多", r"船多货少|(?:运力|可用船舶)(?:相对|较为)?(?:宽松|过剩|充裕)"),
    ("港口拥堵", r"港口(?:拥堵|堵港)"),
    ("天气影响港口作业", r"(?:风雪|大风|降雪|天气|寒流).{0,15}影响港口"),
    ("报价上调", r"报价(?:继续|稳步|小幅|有所)?(?:上调|走高|上涨)"),
    ("报价下调", r"报价(?:继续|小幅|有所)?(?:下调|下跌|下行)"),
    ("报价偏高", r"报价较高"),
    ("交投清淡", r"(?:交投|成交)(?:氛围|节奏)?(?:较为|有所)?(?:冷清|清淡|放缓)"),
    ("交投较活跃", r"(?:交投|成交|交易市场)(?:氛围)?(?:较为)?(?:活跃|升温)"),
    ("船舶周转放缓", r"船舶周转效率较低|周转(?:效率下降|放缓)"),
)
FORECASTS = (
    ("预期运价略有上行", r"向(?:强势|上行)小幅调整|小幅(?:上行|上涨|回升)"),
    ("预期运价偏强", r"向强势调整|偏强|上行|上涨|走强|上调"),
    ("预期运价偏弱", r"向弱调整|偏弱|下行|下跌|走弱|下调"),
    ("预期延续窄幅波动", r"小幅波动|窄幅|震荡|平稳"),
)


def _first_matching(text, rules):
    return next((label for label, pattern in rules if re.search(pattern, text)), None)


def _themed_signals(text, heading):
    # Only use the lead clause for direction. Directions elsewhere may refer
    # to individual routes, past sessions, or the outlook.
    current, _, forecast = text.partition("预计")
    lead = re.split(r"[。;，,]", current, maxsplit=1)[0][:50]
    direction = _first_matching(lead, DIRECTIONS)
    signals = []
    if direction:
        signals.append(f"{heading} · {direction}")

    regions = list(REGION.finditer(current))
    prelude = current[:regions[0].start()] if regions else current
    drivers = [label for label, pattern in DRIVERS if re.search(pattern, prelude)]
    if drivers:
        signals.append(f"{heading} · {'、'.join(drivers[:3])}")

    for index, region in enumerate(regions):
        boundary = regions[index + 1].start() if index + 1 < len(regions) else len(current)
        details = current[region.end():boundary]
        lead = re.split(r"[。;，,]", details, maxsplit=1)[0][:50]
        freight_clause = re.search(r"运价[^。;,，]{0,22}", details)
        movement = _first_matching(lead, DIRECTIONS)
        if not movement and freight_clause:
            movement = _first_matching(freight_clause[0], DIRECTIONS)
        events = [label for label, pattern in DRIVERS if re.search(pattern, details)]
        observations = ([movement] if movement else []) + events
        if observations:
            signals.append(f"{REGION_LABELS[region.lastgroup]} · {'、'.join(observations[:4])}")

    if forecast:
        outlook = _first_matching(forecast.split("。", 1)[0], FORECASTS)
        if outlook:
            signals.append(f"日报展望 · {outlook}")
    return list(dict.fromkeys(signals))


def extract_market_signals(text: str) -> dict[str, list[str]]:
    """Collect supported signals by ship class without exposing OCR paragraphs."""
    if not isinstance(text, str):
        return {}
    report = normalize("NFKC", text)
    chapter = re.search(r"市场\s*(?:资讯|信息|分析|评述|评论)", report)
    if chapter:
        report = report[chapter.end():]
    elif not re.match(r"\s*(?:今日|当日|今天|本日)", report):
        return {}
    report = re.split(r"加入\s*Mysteel|内容咨询|VIP\s*群|免责声明", report, 1)[0]
    report = re.sub(r"\s+", "", report)

    headings = [(match.start(), match.end(), match.lastgroup) for match in VESSEL.finditer(report)]
    headings.extend((match.start(), match.end(), "market") for match in MARKET.finditer(report))
    headings.sort()

    result = {}
    for index, (_, start, kind) in enumerate(headings):
        stop = headings[index + 1][0] if index + 1 < len(headings) else len(report)
        topic = report[start:stop].lstrip(",:")
        # The overall heading often precedes a separate 'today's market' phrase.
        topic = re.sub(r"^(?:今日|当日)?国际干散货(?:航运)?市场", "", topic)
        label = "整体干散货" if kind == "market" else "船型走势"
        if signals := _themed_signals(topic, label):
            items = result.setdefault(kind, [])
            items.extend(signal for signal in signals if signal not in items)
    return result
