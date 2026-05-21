"""Wechat hotspot article generator package."""

from .demo_writer import build_demo_article
from .pipeline import DailyWechatHotspotPipeline

__all__ = ["DailyWechatHotspotPipeline", "build_demo_article"]
