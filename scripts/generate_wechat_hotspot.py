from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import sys


ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from wechat_hotspot import DailyWechatHotspotPipeline, build_demo_article
from wechat_hotspot.news import ShippingNewsCollector


def main() -> None:
    run_date = datetime.now(timezone.utc)
    try:
        pipeline = DailyWechatHotspotPipeline()
        result = pipeline.run(run_date=run_date)
    except Exception as exc:
        if "OPENAI_API_KEY" not in str(exc):
            print(f"生成失败: {exc}")
            raise SystemExit(1) from exc
        collector = ShippingNewsCollector()
        articles = collector.collect(hours=24, target_count=8)
        if len(articles) < 6:
            articles = collector.collect(hours=48, target_count=8)
        article = build_demo_article(articles, run_date=run_date)
        print("未检测到 OPENAI_API_KEY，以下为本地预览稿：\n")
        print(article)
        return
    print(f"文章已生成: {result.output_path}")
    print(f"标题: {result.title}")
    print(f"新闻窗口: 最近 {result.used_hours_window} 小时")
    print(f"候选主题数: {result.candidate_count}")
    print(f"抓取文章数: {result.article_count}")
    print("来源:")
    for source in result.sources:
        print(f"- {source}")


if __name__ == "__main__":
    main()
