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

## 部署成公网网站

当前项目已经补好了 Render 一键部署配置。

### Render 一键部署

1. 把当前项目上传到你的 GitHub 仓库
2. 登录 Render
3. 进入 `New` -> `Blueprint`
4. 选择你的 GitHub 仓库
5. Render 会自动识别仓库里的 `render.yaml`
6. 点击创建并等待构建完成

部署完成后，Render 会给你一个公网网址，类似：

```text
https://shipping-dashboard.onrender.com
```

你和别人访问首页都用这个网址：

```text
https://你的Render服务名.onrender.com
```

接口地址：

```text
https://你的Render服务名.onrender.com/api/dashboard
```

健康检查：

```text
https://你的Render服务名.onrender.com/api/health
```

如果你把 `render.yaml` 里的服务名改成别的，最终网址也会对应变化。

Render 会自动注入 `PORT` 环境变量，当前项目已经兼容，不需要你手动改端口。

### 云服务器部署

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
