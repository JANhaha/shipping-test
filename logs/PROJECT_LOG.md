# Project Log

> 记录 `shipping_project` 的关键变更、验证、发布状态和下次接手提示。新增日志请使用 `skills/project-log/SKILL.md` 的格式。




















## 2026-08-20 10:45 +0800 - 修复网站不更新与缓存问题

触发来源：site.refresh

用户需求：
- 网站看起来没有更新，要求排查并修复，确保页面显示最新数据。

完成内容：
- 排查确认数据管线正常：GitHub Actions 每 5 分钟成功运行，Gmail 同步正常，stable 分支数据已是 2026-08-20 最新报告。
- 根因是 GitHub Pages/CDN 与浏览器缓存导致页面仍读取旧版本；为 11 个页面加入 no-cache meta，并将 CSS/JS 资源版本统一提升到 20260820r1。
- 本地执行 full_refresh 成功同步 6 封邮件，最新源为 `SSY SINGAPORE REPORT- 20 AUG 2026`，静态数据于 10:40 重新生成。
- 通过 GitHub API base64 二进制安全发布 18 个文件到 stable，提交 cfc9bbc92e6549c966b07bbd8d1addac402ea42f。

关键文件：
- docs/index.html、docs/wechat-home.html、docs/market-overview.html、docs/map-data.html、docs/route-rentals-v3.html、docs/market-section.html
- docs/assets/ocean-ui.css、docs/assets/company.css、docs/assets/wechat-lock.js
- docs/data/dashboard.json、docs/data/map_data.json、docs/data/refresh_status.json、docs/data/shipping_data.json
- templates/ 下对应模板

验证：
- GitHub Pages 状态 built。
- https://www.mandarineocean.cn/ 与 /market-overview.html、/map-data.html、/route-rentals-v3.html、/wechat-home.html 均返回 200。
- 线上页面已包含 20260820r1、no-cache meta、小编ANDY维护注记和免责声明。
- 线上 refresh_status 为 2026-08-20T10:40:43+08:00，dashboard/map_data 均指向 20 AUG 2026 报告，route_count 120、fallback false。
- logo、CSS、wechat-lock.js 等资源均 200。

发布状态：
- stable 分支已更新，GitHub Pages 已构建完成。

风险与待办：
- GitHub Pages CDN 可能对最近更新的 HTML 仍缓存约 10 分钟；若浏览器仍显示旧版，请用强制刷新或带版本参数访问。
- 数据文件继续由 5 分钟工作流自动更新，页面内使用时间戳参数拉取，避免浏览器复用旧 JSON。

下次接手提示：
- 若再次出现“网站没更新”，先看 https://www.mandarineocean.cn/data/refresh_status.json 与 GitHub Actions 最近一次运行，再判断是数据源还是缓存问题。

## 2026-08-19 +0800 - 按最新航次表更新公司主页陈旧信息

触发来源：site.content.update

用户需求：
- 根据最新 OcrmVoyagesContractEntity.xlsx 航次表更新公司主页陈旧信息，避免继续展示 2024/2025 旧航次和错误运力范围。

完成内容：
- 首页与微信主页统计条更新：98 → 230+，8.5K-81.6K → 24K-58K（对应公司自有船队载重吨范围）。
- 近期业务实绩表替换为 2026 最新航次（Daisy / Ana / Cathy / Lucy / Joint Mandarine / Lily / Kira / Dina / Yu Ming），并修正 Novorossiysk 拼写。
- 航线网络更新为西非、南美东岸、东南亚与大洋洲、欧洲与地中海、中东及印度洋等全球覆盖；远东市场网络改为全球航线网络。
- 同步 docs/index.html、docs/wechat-home.html、templates/index.html、templates/wechat_home.html，并同步三个市场工具模板。

验证：
- 本地确认四个主页文件中无 98 / 8.5K / 81.6K / 远东市场等旧字段。
- GitHub API 原子提交到 stable，提交 f417e19a6ec3cfe8ca60ab848d9ea8d988fb30e4。
- 线上 https://www.mandarineocean.cn/ 与 /wechat-home.html 均返回 200，包含 230+、24K-58K、MV Yu Ming。

发布状态：
- stable 分支已更新，GitHub Pages 构建已触发。
- 中文文件使用 base64 二进制安全方式发布。

风险与待办：
- 本地 Git 工作区仍保持未提交状态，与线上 stable 通过 API 发布保持一致即可；后续如需本地对齐需成功 fetch 后再处理。
- 后续新航次表更新时继续以结束日期降序取最新航次替换业务实绩区。

下次接手提示：
- 公司主页实绩区改 docs/index.html、docs/wechat-home.html、templates/index.html、templates/wechat_home.html 四处同步。
- 统计条口径：230+ 为航次表有效记录数，24K-58K 为公司自有船队载重吨范围。

## 2026-08-18 17:30 +0800 - 新增微信主页落地页与小编反馈入口

触发来源：site.content.update

用户需求：
- 新增公众号菜单可用的汉洋主页落地页，展示公司首页内容但不含三个市场工具跳转；首页联系租船团队下方增加公众号投稿与网站运维反馈邮箱。

完成内容：
- docs/wechat-home.html 与 templates/wechat_home.html 使用 data-lock=always 并移除导航、市场总览/航线地图/航线租金入口；docs/index.html 与 templates/index.html 增加小编ANDY反馈行，邮箱 deutjan@gmail.com；company.css 增加 feedback-note 样式。

关键文件：
- docs/wechat-home.html
- templates/wechat_home.html
- docs/index.html
- templates/index.html
- docs/assets/company.css

验证：
- GitHub Pages 构建 built；线上首页与 wechat-home.html 均返回 200，包含反馈邮箱与2014介绍，微信主页无 market-overview/map-data/route-rentals 链接。

发布状态：
- stable 分支已更新，微信菜单可使用 https://www.mandarineocean.cn/wechat-home.html

风险与待办：
- 项目内无公众号菜单 API 凭证，公众号后台菜单项需手动配置该链接。

下次接手提示：
- 在公众号后台自定义菜单中新增汉洋主页并指向 wechat-home.html

## 2026-08-18 17:14 +0800 - 首页业务实绩精简为近期航次

触发来源：site.content.update

用户需求：
- 按用户要求移除 2024 年旧航次，保留 2025-2026 近期航次，减少首页信息堆叠。

完成内容：
- docs/index.html 与 templates/index.html 业务实绩表现保留 Candour 8、Daisy Ocean、Lily Ocean、Cathy Ocean、Joint Mandarine、Lucy Ocean、Kira Ocean、Ana Ocean 等近期航次。

关键文件：
- docs/index.html
- templates/index.html

验证：
- 线上 https://www.mandarineocean.cn/ 已确认无 MV Chang Ning / MV Pansolar 等 2024 旧记录，保留近期航次；Pages 构建状态 built。

发布状态：
- stable 分支已更新

风险与待办：
- 无

下次接手提示：
- 后续若 Excel 航次表更新，继续只补充近期航次

## 2026-08-18 16:59 +0800 - 首页公司介绍与业务实绩更新

触发来源：site.content.update

用户需求：
- 删除首页木材运输字样，更新为2014年上海7艘单层甲板重吊船中文介绍，并按Excel航次表补充近期业务实绩。

完成内容：
- 同步 docs/index.html 与 templates/index.html，按 OcrmVoyagesContractEntity.xlsx 补充 2024-2026 相关航次，仅保留与公司业务相关的新航次。

关键文件：
- docs/index.html
- templates/index.html

验证：
- 线上 https://www.mandarineocean.cn/ 已显示2014年介绍、7艘重吊船及新增航次；已确认无木材运输字样；GitHub Pages 构建状态 built。

发布状态：
- stable 分支已更新 docs/index.html 与 templates/index.html

风险与待办：
- 无

下次接手提示：
- 后续航次表更新时继续同步业务实绩表

## 2026-08-18 15:08 +0800 - 航运指数微信入口永久单页化

触发来源：site.ui.update

用户需求：
- 用户反馈微信跳转仍可见导航和切换入口，原因是独立市场分栏页 market-section.html 未接入锁定且被桌面浏览器打开。现将该页改为永久锁定单页：移除顶部导航、品牌跳转和板块切换按钮，页面中不再存在任何可点击跳转链接。

完成内容：
- wechat-lock.js 增加 data-lock=always 与 ?lock=1 支持；market-section.html 标记 data-lock=always，导航与 view-switch 全部移除；其余正式页面升级锁定脚本版本。

关键文件：
- docs/assets/wechat-lock.js
- docs/market-section.html
- docs/index.html
- docs/market-overview.html
- docs/map-data.html
- docs/route-rentals-v3.html
- templates/index.html
- templates/market_overview.html
- templates/map_data.html
- templates/route_rentals_v3.html

验证：
- node --check 通过；线上 market-section.html 仅剩 1 个 href（样式表），无任何 a 标签跳转；脚本支持永久锁定。

发布状态：
- 已通过 GitHub API 推送 stable，Pages 构建 32109772742 部署成功。

风险与待办：
- 普通浏览器打开 market-section.html 也会保持单页；如需市场总览等其它页面，仍使用市场总览、航线地图、航线租金正式页面。

下次接手提示：
- 继续查看本日志和最近 Git 变更。

## 2026-08-18 14:53 +0800 - 微信阅读锁定：页面内只展示当前内容

触发来源：site.ui.update

用户需求：
- 从微信打开网站时自动锁定当前页面，隐藏导航、首页项目入口和视图切换按钮，并拦截跳转到其他页面的点击，避免微信跳转后看到航线地图等其他内容。

完成内容：
- 新增 docs/assets/wechat-lock.js，微信 UA 或 ?wechat=1 时启用锁定；同步更新 docs 与 templates 所有正式页面及样式缓存版本。

关键文件：
- docs/assets/wechat-lock.js
- docs/assets/ocean-ui.css
- docs/index.html
- docs/market-overview.html
- docs/map-data.html
- docs/route-rentals-v3.html
- templates/index.html
- templates/market_overview.html
- templates/map_data.html
- templates/route_rentals_v3.html
- docs/market-section.html

验证：
- node --check 通过；线上 4 个正式页面均包含锁定脚本与新版 CSS，JS/CSS 静态资源返回 200。

发布状态：
- 已通过 GitHub API 推送 stable，Pages 构建 32108372532 部署成功。

风险与待办：
- 普通浏览器访问不受影响；如需强制预览微信模式，可在网址后追加 ?wechat=1。

下次接手提示：
- 继续查看本日志和最近 Git 变更。

## 2026-08-18 14:42 +0800 - 全站添加运营维护标识与免责声明

触发来源：site.ui.update

用户需求：
- 所有正式页面顶部增加「公司网站运营维护：小编ANDY」小字，底部增加指定免责声明，并刷新 CSS 缓存版本。

完成内容：
- 同步修改 docs 静态页与 Flask templates，统一使用 site-ops-note 与 legal-disclaimer 样式，保持公司官网风格且不引入多余宣传文字。

关键文件：
- docs/assets/ocean-ui.css
- docs/index.html
- docs/market-overview.html
- docs/map-data.html
- docs/route-rentals-v3.html
- templates/index.html
- templates/market_overview.html
- templates/map_data.html
- templates/route_rentals_v3.html
- docs/market-section.html

验证：
- 线上 4 个正式页面均返回 200，且均包含顶部标识与免责声明；线上 CSS 已包含新样式。

发布状态：
- 已通过 GitHub API 推送 stable，Pages 构建 32107512942 部署成功。

风险与待办：
- 本地分支与 stable 仍有历史同步差异，属已知状态，不影响本次线上发布。

下次接手提示：
- 继续查看本日志和最近 Git 变更。

## 2026-08-18 14:27 +0800 - 移除网站全部外部来源字样

触发来源：site.content.cleanup

用户需求：
- 删除市场总览、航线地图、航线租金页面中的 SSY、来源、Source 字样，只保留 MANDARINE OCEAN / 漢洋海运

完成内容：
- 市场总览副标题改为最新市场快照；航线地图移除 Source 标签；航线租金移除 SSY/Baltic 说明、来源列、卡片来源信息和邮件主题，来源信息统一显示为漢洋海运；docs 与 templates 同步修改

关键文件：
- docs/market-overview.html
- docs/map-data.html
- docs/route-rentals-v3.html
- templates/market_overview.html
- templates/map_data.html
- templates/route_rentals_v3.html

验证：
- 本地与 stable 三页 SSY=0、来源=0；live 页面 HTTP 200；route-rentals 页面含漢洋海运；Pages 构建 32106796837 success

发布状态：
- 已通过 GitHub API 更新 stable，线上已发布

风险与待办：
- 后续 Gmail 工作流仍会保留邮件主题等内部数据，但页面不再展示外部来源

下次接手提示：
- 继续观察页面刷新，若再出现 SSY 字样优先检查新增渲染逻辑是否重新引入 source_message.subject

## 2026-08-18 11:08 +0800 - 恢复 Gmail 授权并刷新线上数据

触发来源：gmail.refresh.recovered

用户需求：
- 确认 Gmail token 已过期或被撤销，重新完成 OAuth 授权并同步 GitHub Secret

完成内容：
- 最新工作流日志显示 Gmail token 已过期或被撤销；重新运行 gmail_oauth_setup.py 完成 OAuth，credentials/gmail_token.json 与 GMAIL_TOKEN_JSON 均已更新；本地实测可读取 8 封邮件；触发 30 天回溯工作流成功同步 22 封邮件

关键文件：
- credentials/gmail_token.json
- GitHub Secret GMAIL_TOKEN_JSON
- docs/data/refresh_status.json

验证：
- 本地 sync 成功；云端运行 32094203040 成功；线上 refresh_status.json gmail_sync_ok=true，last_attempt_at_beijing=2026-08-18T11:06:56+08:00；Gmail sync health check passed

发布状态：
- Update Shipping Data 已推送 stable，GitHub Pages 后续自动发布

风险与待办：
- Google Cloud OAuth consent screen 若仍为 Testing，refresh token 仍可能周期性失效；长期需发布为 Production

下次接手提示：
- 观察后续定时工作流；若再次 invalid_grant，优先检查 Google Cloud OAuth 发布状态

## 2026-08-18 10:01 +0800 - 恢复公司官网本机访问

触发来源：troubleshooting

用户需求：
- 排查并修复 Edge 经系统代理无法打开 www.mandarineocean.cn

完成内容：
- DNS/HTTPS/GitHub Pages 均正常；确认 Clash 代理链路 TLS 握手失败，系统代理白名单缺失；已加入 mandarineocean.cn 直连例外并写入 Clash Verge 持久配置，刷新 DNS 与 WinINet，重启 Edge 网络进程

关键文件：
- Windows Internet Settings ProxyOverride
- Clash Verge verge.yaml
- Edge NetworkService

验证：
- DNS 解析正常；直连 curl HTTP 200；Invoke-WebRequest HTTP 200；最新 Pages 构建 success；Edge 网络进程已重建

发布状态：
- 网站线上无需改动，www.mandarineocean.cn 在线

风险与待办：
- Clash 重启后需确认系统代理白名单仍保留；如仍有问题优先检查 Clash 侧直连规则

下次接手提示：
- 后续持续观察，若再出现打不开先看 ProxyOverride 是否被 Clash 覆盖

## 2026-07-24 13:45 +0800 - 恢复本机浏览器访问公司网站

触发来源：site.access.recovered

用户需求：
- 排查网站打不开问题，确认站点服务正常并修复 Edge 经系统代理访问时的连接关闭故障。

完成内容：
- 核验 DNS、HTTPS 与 GitHub Pages 均正常；复现 Edge ERR_CONNECTION_CLOSED；确认系统代理为 Clash 127.0.0.1:7897；为 mandarineocean.cn 增加直连例外、刷新 DNS 与 WinINet 设置，并重启 Edge 网络子进程而不关闭标签页。

关键文件：
- Windows Internet Settings ProxyOverride
- Edge NetworkService

验证：
- www 域名返回 HTTP 200，裸域名正确跳转；IPv4 直连和代理 curl 均返回 200；Edge 实际打开首页成功，标题和 3 个项目入口正常，页面控制台无错误。

发布状态：
- 网站端无需代码回滚或重新部署；最近 Update Shipping Data 与 Pages 发布均为 success。

风险与待办：
- 该修复只调整本机代理绕过列表，不影响网站线上内容；GitHub Pages 在部分网络环境仍可能存在跨境链路波动。

下次接手提示：
- 继续观察访问延迟；如需要面向中国大陆长期稳定访问，应迁移至带中国线路的对象存储或 CDN。

## 2026-07-22 18:01 +0800 - 修复 Gmail 数据更新失败与健康检查误报

触发来源：gmail.refresh.recovered

用户需求：
- 定位并修复 Gmail refresh token 失效导致的更新失败邮件，恢复授权并让可降级场景不再错误标记整条任务失败。

完成内容：
- 复现 invalid_grant；重新完成 Gmail OAuth 并同步 GMAIL_TOKEN_JSON；新增可测试的刷新健康检查脚本；REQUIRE_GMAIL_SYNC=false 时保留缓存并发出 warning，true 时继续严格失败；手动执行 30 天全量刷新。

关键文件：
- .github/workflows/update-shipping-data.yml
- scripts/check_refresh_health.py
- tests/test_refresh_health.py
- docs/data/shipping_data.json
- docs/data/map_data.json
- docs/data/dashboard.json
- docs/data/refresh_status.json

验证：
- 14 项 unittest 全部通过；Update Shipping Data 运行 29909986217 成功并读取 16 封邮件；Pages 运行 29910073359 成功；正式站点 gmail_sync_ok=true，更新时间 2026-07-22 17:58，来源邮件为 SSY SINGAPORE REPORT- 22 JULY 2026。

发布状态：
- 修复提交 db38e0d 与数据提交 e543a3f 已进入 stable，GitHub Pages 发布成功。

风险与待办：
- 如 Google Cloud OAuth consent screen 仍处于 Testing，refresh token 仍可能周期性失效；本次已避免失效时持续发送失败邮件，但长期应确认应用发布状态。

下次接手提示：
- 在 Google Cloud Console 确认 OAuth 应用处于 Production，并观察后续定时任务连续成功。

## 2026-07-21 13:56 +0800 - 优化公司官网文案与租船联系方式

触发来源：site.homepage.refined

用户需求：
- 清除不适合公司官网展示的来源、历史参考和注册地址文案，改用公司化业务表达并新增三位租船联系人。

完成内容：
- 重写业务概览、货物经验、全球网络和业务实绩文案；重新设计租船联系人目录；增强移动端长邮箱换行与版式适配；增加首页禁用文案和联系人回归测试。

关键文件：
- docs/index.html
- templates/index.html
- docs/assets/company.css
- tests/test_app_smoke.py

验证：
- 10 项 unittest 全部通过；git diff --check 通过；桌面与手机端实机浏览器检查通过；正式域名返回 200，三位联系人可见且禁用文案均不存在。

发布状态：
- 提交 b506772 已推送至 stable，GitHub Pages 运行 29805384730 发布成功。

风险与待办：
- 当前发布无阻塞风险；Pages 构建提示部分官方 Action 的 Node.js 20 兼容弃用警告，但本次部署成功。

下次接手提示：
- 后续更新 GitHub Actions 依赖版本，并持续检查移动端显示和公开联系方式准确性。

## 2026-07-21 13:21 +0800 - 上线公司宣传首页并全量刷新 Gmail

触发来源：deploy

用户需求：
- 将网站首页改为基于公司附件的专业宣传页，移除公开航运数据栏目，保留市场总览、航线地图和航线租金三个项目，并重新读取 Gmail 全部相关信息。

完成内容：
- 从 Mandarine Ocean 公司 PDF 提取品牌、业务、航线、98 条历史租约记录及真实货运图片；原首页迁移为市场总览；统一三个项目导航与旧地址跳转；90 天回溯同步 100 封 shipping-data 标签邮件并强制解析附件；重新生成 dashboard、map_data、shipping_data 和 refresh_status。

关键文件：
- docs/index.html
- docs/market-overview.html
- docs/map-data.html
- docs/route-rentals-v3.html
- docs/assets/company.css
- docs/assets/company/
- templates/index.html
- templates/market_overview.html
- app.py
- docs/data/shipping_data.json
- docs/data/map_data.json
- docs/data/dashboard.json
- docs/data/refresh_status.json
- tests/test_app_smoke.py

验证：
- 10 项 unittest 全部通过
- py_compile 与 6 个页面内联脚本语法检查通过
- UTF-8 连续问号扫描为 0
- 桌面 1440x900 和手机 390x844 无非预期横向溢出
- 最新来源 SSY SINGAPORE REPORT- 21 JULY 2026 收件时间 09:39 +08:00
- 地图 120 条航线且 SVG 非空
- 航线租金 31 条现货且 Dry FFA 独立
- 云端 Gmail 工作流 29802979603 成功
- Pages 工作流 29803108097 成功
- 正式站点四个 HTML 响应 200 且文件长度与 Git blob 一致

发布状态：
- stable 主页面提交 e536621 已推送
- 云端数据提交 2c2d5e6 已生成
- GitHub Pages 已部署成功
- 正式首页 https://www.mandarineocean.cn/
- 市场总览 https://www.mandarineocean.cn/market-overview.html
- 航线地图 https://www.mandarineocean.cn/map-data.html
- 航线租金 https://www.mandarineocean.cn/route-rentals-v3.html

风险与待办：
- GitHub Pages Cache-Control 为 max-age=600，边缘节点最多可能短暂保留旧响应
- 若 Google Cloud OAuth consent screen 仍处于 Testing，refresh token 仍有周期失效风险；当前本机与云端自动工作流均授权正常

下次接手提示：
- 后续先查看 refresh_status.json 和 Update Shipping Data 工作流；公司首页资料来源为 2024 PDF，新增公司实绩时同步更新附件口径和历史说明。

## 2026-07-15 11:38 +0800 - 恢复 Gmail 授权并修复刷新时间

触发来源：data-refresh

用户需求：
- 重新完成 Gmail OAuth 授权并同步 GitHub Secret，强制回溯邮件、更新全站数据，同时修复 UTC 时间误差和刷新任务假成功问题。

完成内容：
- 最新来源为 SSY SINGAPORE REPORT- 15 JULY 2026；线上 Gmail 状态为正常，邮件接收和同步时间统一为带 +08:00 的北京时间；手动与定时刷新改为串行执行；新增 Gmail 健康检查，授权失效时工作流明确失败。

关键文件：
- .github/workflows/update-shipping-data.yml
- data/gmail_service.py
- tests/test_app_smoke.py
- docs/data/shipping_data.json
- docs/data/map_data.json
- docs/data/dashboard.json
- docs/data/refresh_status.json

验证：
- 8 项 unittest 通过；Python 编译通过；本地 Gmail 抓取成功；GitHub Actions 29386893606 成功并通过 Gmail health check；线上 JSON 显示 gmail_sync_ok=true、最新邮件 2026-07-15 09:48:40+08:00、9 个附件。

发布状态：
- GitHub Pages 29386940068 部署成功：https://www.mandarineocean.cn/

风险与待办：
- 若 Google Cloud OAuth 应用仍处于 Testing，refresh token 仍可能被 Google 周期性撤销；代码无法绕过 Google 的交互授权，需将 OAuth consent screen 发布为 Production 才能长期避免反复授权。

下次接手提示：
- 观察下一次定时任务；若再次出现 invalid_grant，优先检查 Google Cloud OAuth 发布状态，而不是重复修改网页刷新代码。

## 2026-07-12 00:11 +0800 - 补齐四页静默自动更新

触发来源：deploy

用户需求：
- 继续优化四个看板的数据检查与阅读体验，让新快照自动更新且不改变当前阅读位置。

完成内容：
- 首页、航运数据和地图从仅提示新快照改为静默替换内容并恢复滚动位置；航线租金页新增 5 分钟后台检查、窗口聚焦检查与快照签名；邮箱和地图状态详情改为可见；静态站不可用的同步邮箱按钮强制隐藏；共享 CSS 版本升级为 20260711r2。

关键文件：
- docs/assets/ocean-ui.css
- docs/index.html
- docs/shipping-data.html
- docs/map-data.html
- docs/route-rentals-v3.html
- templates/index.html
- templates/shipping_data.html
- templates/map_data.html
- templates/route_rentals_v3.html

验证：
- python -B -m unittest discover 通过 7 项测试
- 8 个 HTML 脚本解析和重复 ID 检查通过
- 桌面与 390px 手机页面无横向溢出
- 静态同步按钮 computed display 为 none
- 线上 dashboard 和 map 快照为 2026-07-11 23:38
- 线上燃油港口 7 个

发布状态：
- 提交 21f8e3c 已推送 stable
- GitHub Pages 运行 29159270593 成功
- 正式域名已读取 CSS r2 和四页静默更新代码

风险与待办：
- 前端每 5 分钟检查与 GitHub Actions 每 5 分钟生成保持一致；Gmail 或外部行情源没有新内容时继续展示最近一次有效数据
- 航线租金来源邮件日期仍按页面显示的最近有效 SSY 邮件为准

下次接手提示：
- 后续刷新逻辑统一保持 background 检查、快照签名和滚动位置恢复；修改共享 CSS 后继续提升版本参数避免旧缓存。

## 2026-07-11 23:39 +0800 - 统一重构数据中心四页界面

触发来源：deploy

用户需求：
- 删除重复的 Shipping Data Freshness 定时任务，并统一优化首页、航运数据、航线地图和航线租金的视觉与信息层级。

完成内容：
- 新增共享海运数据终端设计系统与固定导航；合并首页重复状态框；压缩各页首屏；地图默认聚焦 Dry 航线并修复手机横向溢出；租金涨跌图改为零轴双向图，FFA 继续独立展示；四页手动刷新保持阅读位置。

关键文件：
- app.py
- docs/assets/ocean-ui.css
- docs/index.html
- docs/shipping-data.html
- docs/map-data.html
- docs/route-rentals-v3.html
- templates/index.html
- templates/shipping_data.html
- templates/map_data.html
- templates/route_rentals_v3.html
- tests/test_app_smoke.py

验证：
- python -B -m unittest discover 通过 7 项测试
- 8 个 HTML 内联脚本解析通过
- 桌面与 390px 手机浏览器检查通过且无横向溢出
- 首页燃油 7 个港口正常
- 地图默认 Dry 航线且画布正常
- 租金页 29 条现货与 6 条 FFA 独立显示
- 线上 HTML 与 26266 字节共享 CSS 均已核验

发布状态：
- 提交 fc9d7a5 已推送 stable
- GitHub Pages 运行 29158224687 成功
- https://www.mandarineocean.cn/ 已上线

风险与待办：
- 地图仍依赖 amCharts CDN；外部网络异常时地图底图可能延迟
- Shipping Data Freshness 自动任务已删除，不再生成后续同名任务框

下次接手提示：
- 后续页面视觉调整优先修改 docs/assets/ocean-ui.css；保持 Dry FFA 与现货数据独立，刷新继续使用静默数据更新。

## 2026-07-02 22:43 +0800 - 修复首页燃油价格消失

触发来源：manual

用户需求：
- 网站首页燃油价格因 BunkerIndex 临时连接失败而不显示，本次增加数据兜底并强制刷新静态数据。

完成内容：
- 燃油价格拉取改为先解析 BunkerIndex，失败或为空时使用最近 dashboard 快照；舟山价格独立刷新并去重；首页燃油表增加空态和兜底提示；重新生成 dashboard.json，恢复 7 个港口燃油价格。

关键文件：
- data/dashboard_service.py
- docs/index.html
- templates/index.html
- docs/data/dashboard.json
- tests/test_app_smoke.py

验证：
- python -B -m unittest discover 通过 6 项测试
- node 首页脚本解析通过
- python -B -m py_compile 通过
- 本地 dashboard.json 确认 bunker_count=7 且 Zhoushan VLSFO=648

发布状态：
- 待提交并同步 GitHub Pages

风险与待办：
- BunkerIndex 如继续拒绝连接，页面会显示最近可用快照并提示兜底；外部源恢复后会自动显示实时解析数据。

下次接手提示：
- 发布后检查线上 /data/dashboard.json 的 bunker_index.ports 数量和首页燃油表显示。

## 2026-06-17 10:51 +0800 - 刷新 2026-06-17 Gmail 航运数据

触发来源：gmail-refresh

用户需求：
- 用户反馈 Gmail 有最新数据，要求再次强制拉取并解决频繁授权问题。

完成内容：
- 成功同步 SSY SINGAPORE REPORT- 17 JUNE 2026；重新生成 shipping_data、map_data、dashboard 和 refresh_status；更新 GitHub Secret GMAIL_TOKEN_JSON；增强 gmail_oauth_setup.py，重新授权后自动尝试同步 GitHub Secret；补充 Testing 模式会导致 refresh token 周期性失效的说明。

关键文件：
- docs/data/shipping_data.json
- docs/data/map_data.json
- docs/data/dashboard.json
- docs/data/refresh_status.json
- scripts/gmail_oauth_setup.py
- data/gmail_service.py
- GMAIL_SETUP.md

验证：
- unittest 通过
- py_compile 通过
- 本地 full_refresh 成功同步 5 封邮件
- 数据源为 SSY SINGAPORE REPORT- 17 JUNE 2026
- 地图市场数据 34 条

发布状态：
- 准备发布 stable 并触发线上工作流复验

风险与待办：
- 若 Google OAuth consent screen 仍为 Testing，refresh token 仍可能周期性失效；需发布到 Production 才是根治。

下次接手提示：
- 如再次提示授权，先检查 Google Cloud OAuth consent screen 是否已 In production。

## 2026-06-16 22:53 +0800 - 修复 Gmail token 过期导致数据不更新

触发来源：troubleshooting

用户需求：
- 页面一直显示旧数据，根因是本地和 GitHub Secret 中的 Gmail token 均被 Google 判定为 expired or revoked。

完成内容：
- 重新完成 Gmail OAuth 授权；同步更新 GitHub Secret GMAIL_TOKEN_JSON；本地强制刷新 Gmail 和静态数据；优化 Gmail 同步逻辑，主报告保持长回看，普通邮件只扫最近 2 天，并复用已解析附件，降低 5 分钟任务延迟。

关键文件：
- data/gmail_service.py
- data/gmail_store.py
- .github/workflows/update-shipping-data.yml
- docs/data/shipping_data.json
- docs/data/map_data.json
- docs/data/dashboard.json
- docs/data/refresh_status.json

验证：
- unittest 通过
- py_compile 通过
- full_refresh 成功同步 21 封邮件
- refresh_status 为 ok
- 地图市场数据 34 条

发布状态：
- 准备发布到 stable 并触发线上工作流复验

风险与待办：
- Google OAuth token 若再次被撤销仍需重新授权；如 OAuth App 处于 Testing 模式，刷新 token 可能周期性失效

下次接手提示：
- 若再次出现旧数据，先看 docs/data/refresh_status.json 和 GitHub Actions 日志中的 Gmail token 状态。

## 2026-06-16 16:18 +08:00 - 数据中心收尾与航线租金看板优化

触发来源：manual

用户需求：
- 排查 Gmail 数据刷新、航线地图不同步、页面自动刷新跳动、推送失败、品牌英文、乱码，以及新增更直观的航线租金板块。

完成内容：
- 修复 Gmail 数据刷新链路的可用性问题，并确认线上数据来自 `SSY SINGAPORE REPORT - 16 JUNE 2026`。
- 将页面自动刷新改为后台检查，避免用户阅读时页面跳动。
- 航线地图增加兜底逻辑：如果 Gmail 最新数据暂不可用，使用最近静态航运数据填充，避免地图空白。
- 首页品牌英文确认使用 `Mandarine Ocean`，不再使用旧的 `HANYANG SHIPPING`。
- 首页新增“航线租金”入口，并新增独立航线租金页面。
- 修复备用发布过程中造成的中文编码乱码问题，后续中文 HTML 发布必须使用二进制安全方式。
- 新版航线租金页升级到 `route-rentals-v3.html`，主看板只展示现货航线；`Dry FFA` 单独作为远期参考，不参与现货排行、上涨面、船型均值和完整矩阵。
- 新增行情图：船型平均涨跌、上涨/下跌面、现货航线波动排行，便于直观判断市场强弱。

关键文件：
- `app.py`
- `docs/index.html`
- `docs/route-rentals.html`
- `docs/route-rentals-v2.html`
- `docs/route-rentals-v3.html`
- `templates/index.html`
- `templates/route_rentals.html`
- `templates/route_rentals_v2.html`
- `templates/route_rentals_v3.html`
- `tests/test_app_smoke.py`
- `data/gmail_service.py`
- `data/attachment_visualization.py`
- `data/map_data_service.py`

验证：
- `python -B -m unittest discover` 通过。
- HTML 内联脚本语法检查通过。
- 本地浏览器验证：航线租金 v3 显示中文，连续问号乱码为 0。
- 本地浏览器验证：主看板为 31 条现货航线，`Dry FFA` 为 3 条单独参考；主表和主排行不包含 `Dry FFA`。
- 线上浏览器验证：`route-rentals-v3.html` 显示 31 条现货航线、3 条 FFA 参考、4 条船型图表行、8 条波动排行。

发布状态：
- 普通 Git HTTPS 推送多次出现 `github.com:443` 连接超时。
- 已使用 GitHub API 二进制安全发布到 `stable` 分支，避免再次破坏中文编码。
- GitHub Pages 部署成功。
- 当前航线租金正式入口：`https://www.mandarineocean.cn/route-rentals-v3.html?v=20260616r3`
- 旧入口 `route-rentals.html` 和 `route-rentals-v2.html` 均跳转到 v3，避免浏览器继续读取旧缓存。

风险与待办：
- 本地 Git 状态可能显示 `ahead/behind`，原因是普通 Git 连接失败后使用 GitHub API 创建了线上提交。本地内容与线上核心页面已验证一致，但以后如需恢复干净 Git 状态，应先成功 fetch 后再对齐。
- GitHub Pages 静态缓存约有延迟；遇到旧页面时优先使用带版本参数的新 URL。
- 后续凡是发布中文 HTML，不要通过会损坏 UTF-8 的 PowerShell 文本管道传输，应使用 base64 或字节方式。

下次接手提示：
- 改航线租金页面时从 `docs/route-rentals-v3.html` 和 `templates/route_rentals_v3.html` 入手；主市场判断必须继续排除 `Dry FFA`，只在单独参考区展示。
