import sys
from pathlib import Path
import os
import subprocess

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from data.gmail_service import GmailShippingDataService


def sync_github_secret(token_path):
    if os.getenv("SKIP_GITHUB_SECRET_SYNC", "").lower() in {"1", "true", "yes"}:
        return
    repo = os.getenv("GITHUB_REPOSITORY", "JANhaha/shipping-test")
    try:
        token_text = Path(token_path).read_text(encoding="utf-8")
        subprocess.run(
            ["gh", "secret", "set", "GMAIL_TOKEN_JSON", "--repo", repo],
            input=token_text,
            text=True,
            check=True,
        )
        print(f"GitHub Secret GMAIL_TOKEN_JSON 已同步到: {repo}")
    except FileNotFoundError:
        print("未找到 gh 命令，请手动同步 GitHub Secret GMAIL_TOKEN_JSON。")
    except subprocess.CalledProcessError:
        print("GitHub Secret GMAIL_TOKEN_JSON 同步失败，请检查 gh 登录状态后手动同步。")


def main():
    service = GmailShippingDataService()
    token_path = service.ensure_oauth_token()
    print(f"Gmail OAuth 完成，token 已保存到: {token_path}")
    sync_github_secret(token_path)


if __name__ == "__main__":
    main()
