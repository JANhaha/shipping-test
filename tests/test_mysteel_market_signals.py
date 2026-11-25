import unittest

from data.mysteel_market_signals import extract_market_signals


class MysteelMarketSignalsTest(unittest.TestCase):
    def test_multiline_capesize_and_panamax_commentary(self):
        text = """
        海型船舶运价指数
        巴拿马型船舶运价指数
        市场资讯
        今日海型船市场整体稳中向好。澳洲市场三家矿商询船活跃，
        港口拥堵、可用运力偏紧，船东报价继续上调；巴西航线市场平稳运行，
        交投氛围较为清淡。巴拿马型船市场整体小幅上行，可用运力偏紧、
        煤炭货盘需求尚可，运价稳中有升。整体来看，今日国际干散货
        市场有所提振，市场运输需求较好，预计向强势调整。
        加入Mysteel铁矿石VIP群，第一时间了解市场动态
        """
        result = extract_market_signals(text)
        self.assertEqual(set(result), {"capesize", "panamax", "market"})
        self.assertIn("船型走势 · 市场偏强", result["capesize"])
        self.assertTrue(any(item.startswith("澳洲航线") and "可用船舶偏紧" in item for item in result["capesize"]))
        self.assertIn("巴西航线 · 持稳、交投清淡", result["capesize"])
        self.assertIn("船型走势 · 小幅上行", result["panamax"])
        self.assertIn("船型走势 · 煤炭货盘有支撑、可用船舶偏紧", result["panamax"])
        self.assertIn("日报展望 · 预期运价偏强", result["market"])

    def test_regional_variation_not_assigned_to_other_ship_type(self):
        result = extract_market_signals(
            "市场资讯\n巴拿马型船市场两洋走势不一。大西洋区域运力供需相对均衡；"
            "太平洋区域船多货少、成交清淡，运价小幅回落。\n"
            "超灵便型船市场小幅回落。灵便型船市场交投清淡。"
        )
        self.assertIn("船型走势 · 走势分化", result["panamax"])
        self.assertIn("大西洋 · 运力供需较均衡", result["panamax"])
        self.assertIn("太平洋 · 小幅回落、货盘跟进有限、可用船舶偏多、交投清淡", result["panamax"])
        self.assertEqual(result["supramax"], ["船型走势 · 小幅回落"])
        self.assertEqual(result["handysize"], ["船型走势 · 交投清淡"])

    def test_does_not_invent_commentary_when_the_chart_has_only_tables(self):
        self.assertEqual(extract_market_signals("巴拿马型船舶运价指数 MP11 25.60 0.10"), {})
