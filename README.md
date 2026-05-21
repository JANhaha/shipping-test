# 漢洋海运数据与热点解码系统

这个项目包含两条稳定主线：

- 航运数据网站：展示航运指数、原油、汇率、铁矿、中行美元折算价、沿海散货、燃油价格、SSY 邮件数据和航线地图。
- 公众号日报：《漢洋海运·热点解码》基于海外权威媒体航运新闻生成约 1200 字中文成稿，并用历史记录减少重复选题。

## 当前目录

```text
shipping_project/
├─ app.py                       # Flask 网站入口
├─ wsgi.py                      # 线上 WSGI 入口
├─ run_public.py                # 本地公开访问启动入口
├─ requirements.txt
├─ data/
│  ├─ dashboard_service.py      # 指数、能源、汇率、燃油等看板数据
│  ├─ gmail_service.py          # Gmail 航运报告同步
│  ├─ gmail_store.py            # 本地邮件数据存储
│  ├─ map_data_service.py       # Baltic 航线地图数据
│  ├─ shipping_data_payload.py  # Shipping Data 页面数据
│  └─ article_history.json      # 热点解码去重历史
├─ docs/                        # GitHub Pages 静态站点
├─ templates/                   # Flask 动态页面模板
├─ scripts/
│  ├─ full_refresh.py           # 完整刷新 docs/data
│  ├─ sync_gmail_shipping_data.py
│  ├─ export_shipping_data_static.py
│  ├─ generate_static_data.py
│  ├─ archive_daily_snapshot.py
│  └─ generate_wechat_hotspot.py
├─ wechat_hotspot/              # 热点解码生成流程
├─ outputs/                     # 公众号成稿输出
└─ tests/
   └─ test_app_smoke.py
```

## 安装

```powershell
py -m pip install -r requirements.txt
```

## 运行网站

```powershell
py app.py
```

默认访问 `http://localhost:5000`。主要页面：

- `/`：综合航运数据看板
- `/shipping-data`：SSY 邮件与附件数据
- `/map-data`：航线地图和航线价格联动

## 刷新静态站点数据

```powershell
py scripts/full_refresh.py
```

运行后会更新：

- `docs/data/dashboard.json`
- `docs/data/shipping_data.json`
- `docs/data/map_data.json`

## 生成《漢洋海运·热点解码》

```powershell
py scripts/generate_wechat_hotspot.py
```

生成成功后会：

- 保存文章到 `outputs/YYYY-MM-DD-热点解码.md`
- 更新 `data/article_history.json`
- 输出标题、新闻时间窗口、候选主题数和来源

常用模型配置：

```powershell
$env:OPENAI_API_KEY="你的 API Key"
$env:OPENAI_BASE_URL="https://api.scnet.cn/api/llm/v1"
$env:OPENAI_MODEL="DeepSeek-R1-Distill-Qwen-7B"
$env:OPENAI_API_MODE="chat_completions"
```

MiniMax 分析服务可选：

```powershell
$env:MINIMAX_API_KEY="你的 MiniMax API Key"
```

## 项目瘦身规则

- 旧版 `data_service_*` 实验链路已移除，当前只保留正在被网站和脚本引用的服务模块。
- 临时发布包、日志、缓存、本地数据库、邮件附件和每日归档快照不进入 Git。
- `archive_daily_snapshot.py` 默认只保留最近 14 天快照，可用 `SNAPSHOT_RETENTION_DAYS` 调整。

## 基础检查

```powershell
py -m unittest discover
```
