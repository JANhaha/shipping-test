# 航运数据看板

这是一个可直接对外展示的 Flask 航运信息网站，自动聚合：

- HiFleet Baltic 指数
- 新浪原油与外汇相关页面
- Mysteel 进口矿指数
- 中国银行美元折算价
- Bunker Index 全球港口油价
- 舟山油价

服务端缓存与前端页面都按 30 分钟刷新。

## 主要文件

```text
shipping_project/
├── app.py
├── run_public.py
├── wsgi.py
├── requirements.txt
├── data/
│   └── dashboard_service.py
└── templates/
    └── index.html
```

## 本机运行

```bash
py -m pip install -r requirements.txt
py app.py
```

浏览器访问：

```text
http://127.0.0.1:5000
```

## GitHub Pages 免信用卡发布

这个项目现在支持直接发布为 GitHub Pages 静态网站，不需要信用卡。

原理：

- `docs/index.html` 是公开页面
- `docs/data/dashboard.json` 是最新数据文件
- GitHub Actions 每 30 分钟自动运行一次抓取脚本并更新 `dashboard.json`

### 开启方式

1. 打开你的 GitHub 仓库
2. 进入 `Settings`
3. 打开 `Pages`
4. 在 `Build and deployment` 里选择：
   `Deploy from a branch`
5. Branch 选择：
   `main`
6. Folder 选择：
   `/docs`
7. 保存

GitHub Pages 生效后，访问地址通常是：

```text
https://JANhaha.github.io/shipping-test/
```

第一次启用后，通常需要等待几分钟。

### 自动更新

仓库里已经带有 GitHub Actions 工作流：

```text
.github/workflows/update-pages-data.yml
```

它会：

- 每 30 分钟自动抓取一次最新数据
- 更新 `docs/data/dashboard.json`
- 自动提交回仓库

## 局域网给别人访问

```bash
py run_public.py
```

然后让同一网络内其他人访问你的电脑 IP：

```text
http://你的局域网IP:8080
```

例如：

```text
http://192.168.1.20:8080
```

注意：

- Windows 防火墙要放行 `8080` 端口
- 你的电脑运行期间，别人才能访问

## 云服务器部署

WSGI 入口：

```text
wsgi:application
```

如果你有云服务器，也可以直接用：

```bash
py run_public.py
```

然后把服务器的 `8080` 端口开放到公网，别人就能通过公网 IP 或域名访问。

如果你想改端口，也可以这样运行：

```bash
set PORT=9090
py run_public.py
```

## 接口

- `GET /`
- `GET /api/dashboard`
- `GET /api/health`

## 当前数据说明

- Bunker Index 中无价格的港口不会显示
- Baltic 指数已改为通过 HiFleet 公共接口抓取
- 页面首次打开时会做一次聚合抓取，之后 30 分钟内走缓存
