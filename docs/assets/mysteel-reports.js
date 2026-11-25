(function () {
  const section = document.getElementById("dry-bulk-report");
  if (!section) return;
  const picker = document.getElementById("mysteelReportPicker");
  const date = document.getElementById("mysteelReportDate");
  const status = document.getElementById("mysteelReportStatus");
  const content = document.getElementById("mysteelReportContent");
  const published = document.getElementById("mysteelReportPublished");
  const facts = document.getElementById("mysteelReportFacts");
  const signals = document.getElementById("mysteelReportSignals");
  const source = document.getElementById("mysteelReportSource");
  const publicationTime = new Intl.DateTimeFormat("zh-CN", {
    timeZone: "Asia/Shanghai",
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    hourCycle: "h23",
  });
  const dateLabel = new Intl.DateTimeFormat("zh-CN", {
    timeZone: "Asia/Shanghai",
    month: "long",
    day: "numeric",
  });
  const number = new Intl.NumberFormat("zh-CN", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
  let reports = [];
  let signature = "";
  let followingLatest = true;
  let request = null;

  function element(tag, className, text) {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined) node.textContent = text;
    return node;
  }

  function validReport(report) {
    try {
      const url = new URL(report.url);
      return url.origin === "https://haiyun.mysteel.com" &&
        /^\/a\/\d{8}\/[\da-f]{16}\.html$/i.test(url.pathname) &&
        !url.username && !url.password && !url.search && !url.hash &&
        Number.isFinite(Date.parse(report.published_at));
    } catch {
      return false;
    }
  }

  function quoteCard(item) {
    const card = element("div", "report-quote");
    const heading = element("dt");
    if (item.code) heading.append(element("span", "report-code", item.code));
    heading.append(document.createTextNode(item.label));
    const price = element("dd");
    if (Number.isFinite(item.value)) {
      price.append(element("span", "report-number", number.format(item.value)));
      price.append(element("span", "report-unit", item.unit));
    } else {
      price.append(element("span", "report-kind", "本期仅披露涨跌"));
    }
    const movement = element("dd", "report-change");
    if (Number.isFinite(item.change)) {
      const direction = item.change > 0 ? "up" : item.change < 0 ? "down" : "";
      const change = (item.change > 0 ? "+" : "") + number.format(item.change);
      movement.append(document.createTextNode("涨跌 "));
      movement.append(element("span", direction, `${change} ${item.unit}`));
    }
    card.append(heading);
    if (item.kind && Number.isFinite(item.value)) card.append(element("dd", "report-kind", item.kind));
    card.append(price);
    if (movement.childNodes.length) card.append(movement);
    return card;
  }

  function showReport() {
    const report = reports.find(item => item.url === date.value);
    if (!report) return;
    const data = (Array.isArray(report.facts) ? report.facts : []).filter(item =>
      item && item.label && item.unit && (Number.isFinite(item.value) || Number.isFinite(item.change)));
    const summary = (Array.isArray(report.summary) ? report.summary : []).filter(item =>
      typeof item === "string" && item.trim());
    published.dateTime = report.published_at;
    published.textContent = publicationTime.format(new Date(report.published_at));
    source.href = report.url;
    facts.replaceChildren(...data.map(quoteCard));
    facts.hidden = data.length === 0;
    signals.replaceChildren(...summary.map(item => element("li", "", item)));
    signals.hidden = summary.length === 0;
    content.hidden = false;
    status.textContent = "本期可用的行情数据暂未同步，稍后自动重试。";
    status.hidden = data.length > 0 || summary.length > 0;
  }

  function loadReports() {
    if (request) return request;
    request = (async () => {
      const response = await fetch(section.dataset.source, {
        cache: "no-store",
        signal: AbortSignal.timeout(10000),
      });
      if (!response.ok) throw new Error("Report list unavailable");
      const result = await response.json();
      const next = Array.isArray(result.reports) ? result.reports.filter(validReport) : [];
      if (!next.length) throw new Error("Report list empty");
      const nextSignature = JSON.stringify(next);
      if (signature === nextSignature) return;
      const prior = followingLatest ? "" : date.value;
      reports = next;
      signature = nextSignature;
      date.replaceChildren(...reports.map((report, index) => {
        const label = dateLabel.format(new Date(report.published_at));
        const option = element("option", "", index === 0 ? `${label}（最新）` : label);
        option.value = report.url;
        return option;
      }));
      date.value = reports.some(item => item.url === prior) ? prior : reports[0].url;
      followingLatest = date.value === reports[0].url;
      picker.hidden = reports.length < 2;
      showReport();
    })().catch(() => {
      if (!reports.length) status.textContent = "日报行情暂时无法加载，页面会自动重试。";
    }).finally(() => { request = null; });
    return request;
  }

  date.addEventListener("change", () => {
    followingLatest = date.value === reports[0]?.url;
    showReport();
  });
  window.addEventListener("mandarine:dashboard-updated", loadReports);
  loadReports();
  window.addEventListener("focus", loadReports);
  window.setInterval(loadReports, 5 * 60 * 1000);
})();
