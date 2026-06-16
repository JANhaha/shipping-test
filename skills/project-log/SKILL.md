---
name: project-log
description: Write or update structured Chinese project logs for shipping_project. Use when Codex finishes code, data, deployment, Gmail refresh, dashboard, static site, hook-generated, handoff, or troubleshooting work and needs to record what changed, why, verification results, deployment state, risks, and next handoff notes.
---

# Project Log

## Output

Append entries to `logs/PROJECT_LOG.md` in Chinese. Keep newest entries near the top. Prefer concrete dates and exact page/data names.

## Workflow

1. Inspect the immediate request, changed files, verification commands, deployment status, and any known failures.
2. Record only meaningful project state. Do not include secrets, tokens, raw Gmail credentials, private email bodies, or noisy terminal output.
3. Distinguish source data changes from UI changes. For this project, call out whether changes affect Gmail sync, static `docs/data/*.json`, Flask templates, GitHub Pages, or dashboard pages.
4. If a normal Git push fails and a GitHub API fallback is used, state that plainly.
5. If GitHub Pages caching is relevant, include the current canonical URL and any old redirect pages.
6. If verification was not run, write that explicitly.

## Entry Format

Use this structure:

```markdown
## YYYY-MM-DD HH:mm +08:00 - 简短标题

触发来源：manual / hook / deploy / data-refresh / troubleshooting

用户需求：
- 用一句话说明用户真正要解决的问题。

完成内容：
- 说明实际完成的变更。
- 说明关键决策，例如 FFA 是否单独展示、是否新增页面版本。

关键文件：
- `path/to/file`

验证：
- 写明测试、脚本检查、浏览器验证、线上检查结果。

发布状态：
- 写明是否已上线、GitHub Pages 是否成功、线上 URL。

风险与待办：
- 写明仍可能影响下一次工作的事项。

下次接手提示：
- 给下一位处理者最需要知道的一句话。
```

## Hook Usage

Use `scripts/project_log_hook.py` as the hook-friendly entry point. It can be called by a future automation, git hook, deployment hook, or manual command.

Example:

```powershell
python scripts/project_log_hook.py `
  --event deploy `
  --summary "航线租金 v3 上线，Dry FFA 单独展示" `
  --files "docs/route-rentals-v3.html,templates/route_rentals_v3.html" `
  --verification "unittest 通过；线上页面 31 条现货、3 条 FFA" `
  --deployment "GitHub Pages stable 已部署"
```

The hook can also pass environment variables:

- `PROJECT_LOG_EVENT`
- `PROJECT_LOG_SUMMARY`
- `PROJECT_LOG_FILES`
- `PROJECT_LOG_VERIFICATION`
- `PROJECT_LOG_DEPLOYMENT`
- `PROJECT_LOG_RISKS`
- `PROJECT_LOG_NEXT`

## Style

- Use concise Chinese.
- Prefer exact numbers: route counts, timestamps, workflow run result, commit or URL.
- Do not over-explain implementation details unless they explain a production issue.
- Never log credentials, access tokens, OAuth secrets, raw private email content, or full command output containing sensitive paths.
