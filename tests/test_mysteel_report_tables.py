from io import BytesIO
import unittest

try:
    from PIL import Image, ImageDraw
except ImportError:
    Image = ImageDraw = None

from data.mysteel_report_tables import extract_report_tables


def cell(x, y, text, confidence=0.98):
    return ([[x - 12, y - 8], [x + 12, y - 8], [x + 12, y + 8], [x - 12, y + 8]], text, confidence)


def row(y, values, centers=(30, 200, 360, 530)):
    return [cell(x, y, value) for x, value in zip(centers, values)]


def png(changes=()):
    image = Image.new("RGB", (600, 700), "white")
    draw = ImageDraw.Draw(image)
    for y, color in changes:
        draw.rectangle((525, y - 4, 535, y + 4), fill=color)
    stream = BytesIO()
    image.save(stream, format="PNG")
    return stream.getvalue()


@unittest.skipIf(Image is None, "Pillow is installed with the optional OCR dependencies")
class ReportTablesTest(unittest.TestCase):
    def test_groups_signs_units_and_missing_change(self):
        cells = [cell(150, 30, "海型船舶运价指数")]
        cells += row(60, ("航线代码", "航线", "今日", "涨跌"))
        cells += row(90, ("MC5", "澳洲黑德兰-中国青岛", "15.96", "0.41"))
        cells += row(120, ("MC3", "巴西图巴朗-中国青岛", "34.93", "0.10"))
        cells += row(150, ("MC4", "几内亚卡姆萨尔-中国青岛", "35.25", "0.00"))
        cells += [cell(150, 180, "巴拿马型船舶运价指数")]
        cells += row(210, ("航线代码", "航线", "今日", "涨跌"))
        cells += row(240, ("MP11", "南非萨尔达尼亚-中国青岛", "25.60"))
        cells += [cell(530, 240, "-0.10", confidence=0.6)]
        cells += [cell(150, 280, "期租航线运价指数")]
        cells += row(310, ("航线", "船型", "今日", "涨跌"))
        cells += row(340, ("中国南方-印尼-中国南方", "超灵便型", "14,352", "-4"))
        cells += row(370, ("印度东海岸-中国北方", "灵便型", "12417", "-42"))
        groups = extract_report_tables(cells, png(((90, "red"), (120, "green"), (370, "red"))))["groups"]
        self.assertEqual([item["code"] for item in groups["capesize"]], ["MC5", "MC3", "MC4"])
        self.assertEqual([item["change"] for item in groups["capesize"]], [0.41, -0.10, 0])
        self.assertIsNone(groups["panamax"][0]["change"])
        self.assertEqual(groups["supramax"][0]["value"], 14352)
        self.assertEqual(groups["supramax"][0]["unit"], "美元/天")
        self.assertEqual(groups["supramax"][0]["change"], -4)
        self.assertIsNone(groups["handysize"][0]["change"])

    def test_distinct_fixture_and_multiline_vessel_sale(self):
        cells = [cell(150, 30, "部分成交汇总")]
        cells += row(60, ("航线", "船型", "合约类型", "成交价"))
        cells += row(90, ("澳洲黑德兰-中国青岛", "海型", "程租", "16.00"))
        cells += [cell(150, 130, "船舶交易")]
        sale_centers = (35, 155, 260, 365, 465, 560)
        cells += row(160, ("船型", "船名", "载重吨", "建造年份", "建造商", "出售价"), sale_centers)
        cells += row(220, ("卡姆萨尔型散货船", " ", "81,788", "2019", "日本大岛", "3,900"), sale_centers)
        cells += [cell(155, 203, "TAHO"), cell(155, 237, "AUSTRALIA"), cell(120, 270, "市场资讯")]
        data = extract_report_tables(cells, png())
        self.assertEqual(data["fixtures"][0]["value"], 16.0)
        self.assertEqual(data["fixtures"][0]["vessel"], "海岬型")
        self.assertEqual(data["sales"][0]["name"], "TAHO AUSTRALIA")
        self.assertEqual(data["sales"][0]["dwt"], 81788)
        self.assertEqual(data["sales"][0]["unit"], "万美元")

    def test_missing_column_anchor_does_not_extract_random_numbers(self):
        cells = [cell(150, 30, "海型船舶运价指数")]
        cells += row(60, ("航线代码", "航线", "今日", "其他"))
        cells += row(90, ("MC5", "澳洲黑德兰-中国青岛", "15.96", "0.41"))
        self.assertEqual(extract_report_tables(cells, png())["groups"], {})
