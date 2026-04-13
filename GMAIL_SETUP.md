# Gmail Shipping Data 接入说明

当前 Flask 项目已新增 Gmail API 集成，满足以下能力：
- 使用 Gmail API + OAuth，不使用 IMAP
- 只读取标签为 `shipping-data` 的邮件
- 只抓取最近 1 天的新邮件
- 提取发件人、主题、时间、正文摘要
- 下载并解析 PDF、Excel 附件
- 结果保存到本地 SQLite 数据库
- 新增网页页面展示邮件和附件解析结果

## 1. 安装依赖

```powershell
py -m pip install -r requirements.txt
```

## 2. 准备 Google OAuth 客户端文件

在 Google Cloud Console 中启用 Gmail API，并创建 OAuth Desktop App 客户端。
将下载得到的客户端文件保存到：

```text
credentials/gmail_credentials.json
```

## 3. 首次授权

```powershell
cd C:\Users\user\Desktop\shipping_project
py scripts\gmail_oauth_setup.py
```

授权完成后会生成：

```text
credentials/gmail_token.json
```

## 4. 手动同步邮件

```powershell
cd C:\Users\user\Desktop\shipping_project
py scripts\sync_gmail_shipping_data.py
```

## 5. 启动 Flask

```powershell
py app.py
```

访问地址：
- 首页：`http://127.0.0.1:5000/`
- 邮件页面：`http://127.0.0.1:5000/shipping-data`
- 邮件接口：`http://127.0.0.1:5000/api/shipping-data`
- 手动同步接口：`POST http://127.0.0.1:5000/api/shipping-data/sync`

## 6. 每日定时运行

可用 Windows 任务计划程序每天执行：

```powershell
py C:\Users\user\Desktop\shipping_project\scripts\sync_gmail_shipping_data.py
```

建议将任务的“起始于”目录设置为：

```text
C:\Users\user\Desktop\shipping_project
```

## 7. 本地文件说明

- 数据库：`data/shipping_data.db`
- 附件目录：`data/gmail_attachments/`
- OAuth 客户端：`credentials/gmail_credentials.json`
- OAuth token：`credentials/gmail_token.json`
