(function () {
  const list = document.getElementById("mysteelReportList");
  const status = document.getElementById("mysteelReportStatus");
  const publicationTime = new Intl.DateTimeFormat("zh-CN", {
    timeZone: "Asia/Shanghai",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    hourCycle: "h23",
  });
  let displayed = "";
  let loading = false;

  function reportEntry(report) {
    const url = new URL(report.url);
    const published = new Date(report.published_at);
    if (url.origin !== "https://haiyun.mysteel.com" ||
        !/^\/a\/\d{8}\/[\da-f]{16}\.html$/i.test(url.pathname) ||
        typeof report.title !== "string" || !report.title || Number.isNaN(published.getTime())) {
      throw new Error("Invalid report metadata");
    }
    const entry = document.createElement("li");
    const link = document.createElement("a");
    link.href = url.href;
    link.target = "_blank";
    link.rel = "noopener";
    link.textContent = report.title;
    const time = document.createElement("time");
    time.dateTime = report.published_at;
    time.textContent = publicationTime.format(published);
    entry.append(link, time);
    return entry;
  }

  async function loadReports() {
    if (loading) return;
    loading = true;
    try {
      const response = await fetch(list.dataset.source, {
        cache: "no-store",
        signal: AbortSignal.timeout(10000),
      });
      if (!response.ok) throw new Error("Report list unavailable");
      const { reports } = await response.json();
      if (!Array.isArray(reports) || !reports.length) throw new Error("Report list empty");
      const signature = JSON.stringify(reports);
      if (displayed !== signature) {
        list.replaceChildren(...reports.map(reportEntry));
        displayed = signature;
      }
      status.hidden = true;
    } catch {
      if (!displayed) status.textContent = "暂时无法读取日报列表，可前往 Mysteel 日报栏目查看。";
    } finally {
      loading = false;
    }
  }

  loadReports();
  window.addEventListener("focus", loadReports);
  window.setInterval(loadReports, 5 * 60 * 1000);
})();
