# Mandarine Ocean Shipping Dashboard

Mandarine Ocean Shipping Dashboard 是一个面向公开展示的航运信息看板。线上版本由 `stable` 分支的 `docs/` 目录发布到 GitHub Pages，并绑定自定义域名：

- GitHub Pages: https://janhaha.github.io/shipping-test/
- Custom domain: http://www.mandarineocean.cn/
- Production branch: `stable`
- Published folder: `docs/`
- Page version: `Version: V2`

## 发布内容

`docs/` 目录包含三类公开页面：

- `docs/index.html`: 综合市场看板
- `docs/shipping-data.html`: 最新 SSY Singapore 邮件与附件结构化数据
- `docs/map-data.html`: Baltic route map 与航线数据

公开数据文件位于 `docs/data/`：

- `dashboard.json`
- `shipping_data.json`
- `map_data.json`

## 自动刷新

GitHub Actions 工作流 `.github/workflows/update-shipping-data.yml` 每 30 分钟运行一次，也支持手动触发。流程会：

1. checkout `stable`
2. 安装 Python 依赖
3. 写入 Gmail OAuth credentials/token secret
4. 运行 `scripts/full_refresh.py`
5. 只提交 `docs/data/*.json`

如果 Gmail 授权暂时失效，流程会保留上一版 Gmail 派生数据，同时继续刷新公开市场数据，避免整站数据发布中断。

## 本地运行

```powershell
py -m pip install -r requirements.txt
py app.py
```

本地页面：

```text
http://127.0.0.1:5000
```

本地完整刷新：

```powershell
py scripts/full_refresh.py
```

Gmail 授权初始化：

```powershell
py scripts/gmail_oauth_setup.py
```

## 主要入口

- `app.py`: Flask 本地服务
- `data/dashboard_service.py`: 市场行情聚合
- `data/gmail_service.py`: Gmail 同步与附件解析
- `data/shipping_data_payload.py`: shipping-data 公开 payload
- `data/map_data_service.py`: map-data 公开 payload
- `scripts/full_refresh.py`: GitHub Pages 数据刷新总入口

## 维护原则

- 发布到网页的内容只从 `stable` 分支的 `docs/` 读取。
- 定时任务只提交 `docs/data/dashboard.json`、`docs/data/shipping_data.json`、`docs/data/map_data.json`。
- credentials、数据库、附件缓存、日报归档和本地输出文件不进入 Git。
- 旧版爬虫和临时测试脚本不要混入发布分支。
