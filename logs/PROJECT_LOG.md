# Project Log

> 记录 `shipping_project` 的关键变更、验证、发布状态和下次接手提示。新增日志请使用 `skills/project-log/SKILL.md` 的格式。





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
