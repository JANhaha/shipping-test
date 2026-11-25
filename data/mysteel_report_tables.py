"""Extract numeric observations from the public Mysteel infographic."""

import math
import re
from dataclasses import dataclass
from io import BytesIO
from unicodedata import normalize


VESSEL_GROUPS = {
    "capesize": "海岬型",
    "panamax": "巴拿马型",
    "supramax": "超灵便型",
    "handysize": "灵便型",
}
NUMBER = re.compile(r"[+-]?(?:\d+|\d{1,3}(?:,\d{3})+)(?:\.\d{1,2})?")
ROUTE_CODE = re.compile(r"M(?:C|P|S|H)\d{1,3}")
MIN_CONFIDENCE = 0.84


@dataclass(frozen=True)
class Cell:
    text: str
    box: tuple[float, float, float, float]

    @property
    def x(self):
        return (self.box[0] + self.box[2]) / 2

    @property
    def y(self):
        return (self.box[1] + self.box[3]) / 2

    @property
    def height(self):
        return self.box[3] - self.box[1]


def _ocr_cells(cells):
    for corners, text, confidence in cells:
        if confidence < MIN_CONFIDENCE or not isinstance(text, str) or len(corners) != 4:
            continue
        x, y = zip(*corners)
        if not all(math.isfinite(value) for value in (*x, *y)):
            continue
        clean = normalize("NFKC", text).strip().replace("−", "-").replace("–", "-")
        if clean:
            yield Cell(clean, (min(x), min(y), max(x), max(y)))


def _vessel_group(text):
    for matcher, group in (
        (r"海[岬峡甲]?型", "capesize"),
        (r"巴拿马型|卡姆萨尔型", "panamax"),
        (r"超灵便型|大灵便型|超极限灵便型", "supramax"),
        (r"灵便型", "handysize"),
    ):
        if re.search(matcher, text):
            return group
    return None


def _section(cell):
    text = cell.text.replace(" ", "")
    if "期租航线运价" in text:
        return "time"
    if "型船" in text and "运价指数" in text:
        return _vessel_group(text)
    if "成交汇总" in text:
        return "fixtures"
    if text == "船舶交易":
        return "sales"
    if text == "市场资讯":
        return "market"
    return None


def _number(text):
    cleaned = text.replace(" ", "")
    if NUMBER.fullmatch(cleaned):
        return float(cleaned.replace(",", ""))
    return None


def _change(cell, image):
    if cell is None:
        return None
    value = _number(cell.text)
    if value is None or value == 0:
        return value
    if image is not None:
        left, top, right, bottom = map(int, cell.box)
        if 0 <= left < right <= image.width and 0 <= top < bottom <= image.height:
            red = green = 0
            crop = image.crop((left, top, right, bottom)).convert("RGB")
            pixels = crop.load()
            for r, g, b in (pixels[x, y] for x in range(crop.width) for y in range(crop.height)):
                red += r > 100 and r - max(g, b) > 45
                green += g > 70 and g - max(r, b) > 28
            # The source prints positive magnitudes in red and negatives in green.
            if red >= 8 and red > 2 * green:
                return value if value > 0 else None
            if green >= 8 and green > 2 * red:
                return -abs(value) if not cell.text.startswith("+") else None
    return value if cell.text.startswith(("+", "-")) else None


def _rows(cells, headers, optional_change=False):
    first_column = headers[0]
    for anchor in cells:
        if anchor.text != first_column:
            continue
        heading = [
            cell for cell in cells
            if abs(cell.y - anchor.y) <= max(12, anchor.height * 0.65)
        ]
        columns = [next((cell for cell in heading if cell.text == name), None) for name in headers]
        if all(columns) and all(a.x < b.x for a, b in zip(columns, columns[1:])):
            break
    else:
        return []

    boundaries = [(a.x + b.x) / 2 for a, b in zip(columns, columns[1:])]
    body = [cell for cell in cells if cell.y > max(header.box[3] for header in columns)]
    rows = []
    for cell in body:
        # The first-column label anchors cells on the same baseline.
        if sum(cell.x > boundary for boundary in boundaries) != 0:
            continue
        band = max(11, cell.height * 0.48)
        row = [[] for _ in headers]
        for other in body:
            if abs(other.y - cell.y) <= band:
                row[sum(other.x > boundary for boundary in boundaries)].append(other)
        if all(len(column) == 1 for column in row):
            rows.append([column[0] for column in row])
        elif optional_change and not row[-1] and all(len(column) == 1 for column in row[:-1]):
            rows.append([column[0] for column in row[:-1]] + [None])
        elif headers == ("船型", "船名", "载重吨", "建造年份", "建造商", "出售价格") and all(
            len(column) == 1 for i, column in enumerate(row) if i != 1
        ):
            # Vessel names sometimes wrap within the sale row.
            name_left, name_right = boundaries[0:2]
            name_band = cell.height * 1.4
            nearest_names = (
                other for other in body
                if name_left < other.x <= name_right and abs(other.y - cell.y) <= name_band
            )
            name_parts = sorted(nearest_names, key=lambda other: other.y)
            if name_parts:
                row[1] = [Cell(" ".join(part.text for part in name_parts), name_parts[0].box)]
                rows.append([column[0] for column in row])
    return rows


def _route_name(text):
    if re.fullmatch(r"[\u3400-\u9fffA-Za-z0-9 ()]+(?:\s*[-—至→]\s*[\u3400-\u9fffA-Za-z0-9 ()]+){1,3}", text):
        return re.sub(r"\s*[-—至→]\s*", " → ", text)
    return None


def _route_rows(cells, section, image):
    if section == "time":
        rows = _rows(cells, ("航线", "船型", "今日", "涨跌"), optional_change=True)
    else:
        rows = _rows(cells, ("航线代码", "航线", "今日", "涨跌"), optional_change=True)
    for first, second, price, movement in rows:
        if section == "time":
            code, label, group = None, _route_name(first.text), _vessel_group(second.text)
            unit, kind, high = "美元/天", "期租运价指数", 200_000
        else:
            code, label, group = first.text.upper(), _route_name(second.text), section
            unit, kind, high = "美元/吨", "程租运价指数", 500
            if not ROUTE_CODE.fullmatch(code) or code[1] != group[0].upper():
                continue
        value = _number(price.text)
        change = _change(movement, image)
        if not group or not label or value is None or not 0 < value <= high:
            continue
        if change is not None and (abs(change) > value or abs(change) > high / 2):
            change = None
        yield group, {
            "code": code, "label": label, "value": value, "change": change,
            "unit": unit, "kind": kind,
        }


def _fixture_rows(cells):
    for route, vessel, contract, price in _rows(cells, ("航线", "船型", "合约类型", "成交价")):
        label = _route_name(route.text)
        group = _vessel_group(vessel.text)
        value = _number(price.text)
        if label and group and contract.text in {"程租", "期租"} and value is not None and 0 < value <= 200_000:
            yield {
                "label": label, "vessel": VESSEL_GROUPS[group], "contract": contract.text,
                "value": value, "unit": "美元",
            }


def _sales_rows(cells):
    # Both final-column labels occur in OCR output.
    relabeled = [
        Cell("出售价格", cell.box) if cell.text in {"出售价", "售价"} else cell
        for cell in cells
    ]
    for vessel, name, dwt, year, builder, price in _rows(
        relabeled, ("船型", "船名", "载重吨", "建造年份", "建造商", "出售价格")
    ):
        tonnage, built, value = (_number(cell.text) for cell in (dwt, year, price))
        if (
            tonnage is None or built is None or value is None
            or not 1_000 <= tonnage <= 500_000
            or not 1950 <= built <= 2100 or not 0 < value <= 30_000
            or not tonnage.is_integer() or not built.is_integer()
            or not re.fullmatch(r"[A-Z0-9][A-Z0-9 .'-]{1,49}", name.text)
        ):
            continue
        vessel_name = re.sub(r"^海[峡甲]?型", "海岬型", vessel.text)
        yield {
            "name": name.text, "vessel": vessel_name, "dwt": int(tonnage),
            "year": int(built), "builder": builder.text, "value": value, "unit": "万美元",
        }


def extract_report_tables(cells, image_bytes):
    """Return recognized structured records, with no article prose or image in the result."""
    from PIL import Image

    ordered = sorted(_ocr_cells(cells), key=lambda cell: cell.y)
    headings = [
        (cell.y, section)
        for cell in ordered
        if (section := _section(cell))
    ]
    result = {"groups": {}, "fixtures": [], "sales": []}
    with Image.open(BytesIO(image_bytes)) as image:
        if image.width * image.height > 20_000_000:
            return result
        for index, (start, section) in enumerate(headings):
            end = headings[index + 1][0] if index + 1 < len(headings) else float("inf")
            group_cells = [cell for cell in ordered if start < cell.y < end]
            if section == "fixtures":
                result["fixtures"].extend(_fixture_rows(group_cells))
            elif section == "sales":
                result["sales"].extend(_sales_rows(group_cells))
            elif section != "market":
                for group, route in _route_rows(group_cells, section, image):
                    result["groups"].setdefault(group, []).append(route)
    return result
