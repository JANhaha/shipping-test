/* Downloading JSON is not the same as syncing Gmail. */
(function () {
  const ENDPOINT = "https://mandarine-refresh.mandarine-refresh-hy.workers.dev/refresh";
  const STATUS_URL = "./data/refresh_status.json";
  const format = new Intl.DateTimeFormat("zh-CN", { timeZone: "Asia/Shanghai", dateStyle: "short", timeStyle: "medium", hour12: false });
  function healthText(status, now = Date.now()) {
    const timestamp = status.last_success_at_beijing || (status.gmail_sync_ok ? status.last_attempt_at_beijing : null);
    const time = Date.parse(timestamp);
    const age = (now - time) / 60000;
    const last = Number.isFinite(time) ? format.format(new Date(time)) + " 北京时间" : "未知";
    if (status.gmail_sync_ok !== true) return `云端 Gmail 同步失败，正在显示旧数据。上次成功：${last}`;
    if (!Number.isFinite(time)) return "无法确认云端同步时间，请手动刷新。";
    if (age > 20) return `云端数据已超过 ${Math.floor(age)} 分钟未同步，请点击刷新数据。上次成功：${last}`;
    return `最近 Gmail 同步成功：${last}。定时器每 5 分钟检查；没有新邮件时，行情日期不会改变。`;
  }
  function completed(status, result, startedAt) {
    return (result.run_id && String(status.run_id) === String(result.run_id)) || Date.parse(status.last_attempt_at_beijing) >= startedAt;
  }
  async function readStatus() {
    const response = await fetch(`${STATUS_URL}?ts=${Date.now()}`, { cache: "no-store", signal: AbortSignal.timeout(15000) });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    return response.json();
  }
  function attach(reload) {
    const button = document.getElementById("refreshBtn");
    const notice = document.createElement("p");
    notice.setAttribute("role", "status");
    notice.style.cssText = "font-size:13px;line-height:1.7;margin:10px 0;color:#31545a";
    button.insertAdjacentElement("afterend", notice);
    let refreshing = false;
    const showHealth = async () => {
      if (refreshing) return;
      try { const status = await readStatus(); if (!refreshing) notice.textContent = healthText(status); }
      catch { if (!refreshing) notice.textContent = "无法读取云端同步状态；页面内容可能是旧快照。"; }
    };
    button.addEventListener("click", async () => {
      if (refreshing) return;
      refreshing = true;
      button.disabled = true;
      const startedAt = Date.now();
      notice.textContent = "正在请求云端重新读取 Gmail 和市场数据…";
      try {
        const response = await fetch(ENDPOINT, { method: "POST", cache: "no-store", signal: AbortSignal.timeout(45000) });
        if (!response.ok) throw new Error(`刷新服务 HTTP ${response.status}`);
        const result = await response.json();
        if (!["queued", "running"].includes(result.status)) throw new Error("刷新服务返回了异常状态");
        notice.textContent = "云端任务已提交，等待同步及网站发布完成（通常需要几分钟）…";
        const deadline = Date.now() + 10 * 60000;
        let verified = false;
        while (Date.now() < deadline) {
          await new Promise(resolve => setTimeout(resolve, 10000));
          let status;
          try { status = await readStatus(); } catch { continue; }
          if (!completed(status, result, startedAt)) continue;
          await reload({ background: true });
          notice.textContent = status.gmail_sync_ok === true ? `刷新完成。${healthText(status)}` : healthText(status);
          verified = true;
          break;
        }
        if (!verified) notice.textContent = "任务已提交，但尚未确认新数据发布。请稍后查看；后台仍会自动检查，不代表刷新成功。";
      } catch (error) {
        notice.textContent = `未能确认刷新：${error.message}。云端定时同步不受本次浏览器连接失败影响。`;
      } finally {
        refreshing = false;
        button.disabled = false;
      }
    });
    showHealth();
    setInterval(showHealth, 5 * 60000);
    window.addEventListener("focus", showHealth);
  }
  globalThis.MandarineRefresh = { attach, healthText, completed };
})();
