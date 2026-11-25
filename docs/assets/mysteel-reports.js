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
  const overview = document.getElementById("mysteelReportOverview");
  const groupNavigation = document.getElementById("mysteelReportVesselNav");
  const groups = document.getElementById("mysteelReportGroups");
  const checkedMeta = document.getElementById("mysteelReportCheckMeta");
  const checked = document.getElementById("mysteelReportChecked");
  const vesselTypes = [
    ["capesize", "海岬型", "Capesize"],
    ["panamax", "巴拿马型", "Panamax"],
    ["supramax", "超灵便型", "Supramax"],
    ["handysize", "灵便型", "Handysize"],
  ];
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
  const whole = new Intl.NumberFormat("zh-CN", { maximumFractionDigits: 0 });
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

  function formatValue(value, unit, signed = false) {
    if (!Number.isFinite(value)) return "—";
    const format = unit === "美元/天" && Number.isInteger(value) ? whole : number;
    return (signed && value > 0 ? "+" : "") + format.format(value);
  }

  function directionClass(change) {
    if (change > 0) return "up";
    if (change < 0) return "down";
    return "";
  }

  function textList(items) {
    return (Array.isArray(items) ? items : []).filter(item => typeof item === "string" && item.trim());
  }

  function quoteList(items) {
    return (Array.isArray(items) ? items : []).filter(item =>
      item && item.label && item.unit && (Number.isFinite(item.value) || Number.isFinite(item.change)));
  }

  function quoteCard(item) {
    const card = element("div", "report-quote");
    const heading = element("dt");
    if (item.code) heading.append(element("span", "report-code", item.code));
    heading.append(document.createTextNode(item.label));
    const price = element("dd");
    if (Number.isFinite(item.value)) {
      price.append(element("span", "report-number", formatValue(item.value, item.unit)));
      price.append(element("span", "report-unit", item.unit));
    } else {
      price.append(element("span", "report-kind", "本期仅披露涨跌"));
    }
    const movement = element("dd", "report-change");
    if (Number.isFinite(item.change)) {
      const direction = directionClass(item.change);
      const change = formatValue(item.change, item.unit, true);
      movement.append(document.createTextNode("涨跌 "));
      movement.append(element("span", direction, `${change} ${item.unit}`));
    }
    card.append(heading);
    if (item.kind && Number.isFinite(item.value)) {
      card.append(element("dd", "report-kind", [item.shipLabel, item.kind].filter(Boolean).join(" · ")));
    }
    card.append(price);
    if (movement.childNodes.length) card.append(movement);
    return card;
  }

  function marketBreadth(rows) {
    const changes = rows.filter(row => Number.isFinite(row.change));
    if (!changes.length) return "";
    const up = changes.filter(row => row.change > 0).length;
    const down = changes.filter(row => row.change < 0).length;
    const flat = changes.length - up - down;
    const counts = [[up, "涨"], [flat, "平"], [down, "跌"]];
    return counts.filter(([count]) => count).map(([count, label]) => `${count} ${label}`).join(" · ");
  }

  function makeTable(label, headings, data) {
    const wrap = element("div", "report-route-table-wrap");
    wrap.tabIndex = 0;
    wrap.setAttribute("role", "region");
    wrap.setAttribute("aria-label", label);
    const table = element("table", "report-route-table");
    const header = element("tr");
    headings.forEach(([name, numeric]) => {
      const cell = element("th", numeric ? "report-numeric" : "", name);
      cell.scope = "col";
      header.append(cell);
    });
    table.createTHead().append(header);
    const body = table.createTBody();
    data.forEach((line) => {
      const row = element("tr");
      line.forEach(([text, className]) => row.append(element("td", className, text)));
      body.append(row);
    });
    wrap.append(table);
    return wrap;
  }

  function groupPanel(id, title, subheading, countText, points, table) {
    const panel = element("section", "report-vessel");
    panel.id = `report-${id}`;
    const header = element("header", "report-vessel-header");
    const heading = element("div");
    heading.append(element("h3", "", title));
    if (subheading) heading.append(element("p", "report-vessel-language", subheading));
    header.append(heading);
    if (countText) header.append(element("span", "report-vessel-count", countText));
    panel.append(header);
    if (points.length) {
      const list = element("ul", "report-vessel-points");
      list.setAttribute("aria-label", `${title}市场要点`);
      list.append(...points.map(point => element("li", "", point)));
      panel.append(list);
    }
    if (table) panel.append(table);
    return panel;
  }

  function vesselTable(name, rows) {
    return makeTable(`${name}航线运价和涨跌`, [
      ["航线"], ["报价口径"], ["运价", true], ["涨跌", true],
    ], rows.map(row => [
      [[row.code, row.label].filter(Boolean).join(" · "), ""],
      [`${row.kind || "航线运价"} · ${row.unit}`, "report-route-meta"],
      [formatValue(row.value, row.unit), "report-numeric"],
      [formatValue(row.change, row.unit, true), `report-numeric ${directionClass(row.change)}`],
    ]));
  }

  function fixtureTable(rows) {
    return makeTable("部分成交汇总", [
      ["航线"], ["船型"], ["合约"], ["成交价", true],
    ], rows.map(row => [
      [row.label, ""], [row.vessel, ""], [row.contract, "report-route-meta"],
      [`${formatValue(row.value, row.unit)} ${row.unit}`, "report-numeric"],
    ]));
  }

  function salesTable(rows) {
    return makeTable("二手船交易", [
      ["船名"], ["船型"], ["载重吨", true], ["建造年份与船厂"], ["金额", true],
    ], rows.map(row => [
      [row.name, ""], [row.vessel, ""],
      [Number.isFinite(row.dwt) ? whole.format(row.dwt) : "—", "report-numeric"],
      [[row.year, row.builder].filter(Boolean).join(" · ") || "—", "report-route-meta"],
      [`${Number.isFinite(row.value) ? whole.format(row.value) : "—"} ${row.unit}`, "report-numeric"],
    ]));
  }

  function renderGroups(report) {
    const panels = [];
    const navigation = [];
    const representatives = [];
    const categorized = report.market_signals || {};
    for (const [id, label, english] of vesselTypes) {
      const rows = quoteList(report.groups?.[id]);
      const points = textList(categorized[id]);
      const breadth = marketBreadth(rows);
      if (breadth) points.push(`航线表现：${breadth}`);
      if (!rows.length && !points.length) continue;
      if (rows.length) representatives.push({ ...rows[0], shipLabel: label });
      panels.push(groupPanel(id, label, english, rows.length ? `${rows.length} 条航线` : "", points,
        rows.length ? vesselTable(label, rows) : null));
      navigation.push([id, label]);
    }
    const fixtures = Array.isArray(report.fixtures) ? report.fixtures : [];
    if (fixtures.length) {
      panels.push(groupPanel("fixtures", "部分成交汇总", "", `${fixtures.length} 条成交`, [], fixtureTable(fixtures)));
      navigation.push(["fixtures", "成交"]);
    }
    const sales = Array.isArray(report.sales) ? report.sales : [];
    if (sales.length) {
      panels.push(groupPanel("sales", "二手船交易", "", `${sales.length} 艘`, [], salesTable(sales)));
      navigation.push(["sales", "二手船"]);
    }
    groups?.replaceChildren(...panels);
    groupNavigation?.replaceChildren(...navigation.map(([id, label]) => {
      const link = element("a", "", label);
      link.href = `#report-${id}`;
      return link;
    }));
    if (groupNavigation) groupNavigation.hidden = !panels.length;
    return representatives;
  }

  function showReport() {
    const report = reports.find(item => item.url === date.value);
    if (!report) return;
    const groupedQuotes = renderGroups(report);
    const data = groupedQuotes.length ? groupedQuotes : quoteList(report.facts);
    const groupSummary = textList(report.market_signals?.market);
    const summary = groupSummary.length ? groupSummary : textList(report.summary).slice(0, groupedQuotes.length ? 1 : 4);
    published.dateTime = report.published_at;
    published.textContent = publicationTime.format(new Date(report.published_at));
    source.href = report.url;
    facts.replaceChildren(...data.map(quoteCard));
    facts.hidden = data.length === 0;
    signals.replaceChildren(...summary.map(item => element("li", "", item)));
    signals.hidden = summary.length === 0;
    if (overview) overview.hidden = !data.length && !summary.length;
    content.hidden = false;
    status.textContent = groupedQuotes.length
      ? "本期部分航线待核对，已核对的数据见下方。"
      : "本期分船型数据待同步，已披露的摘要见下方。";
    status.hidden = report.grouped_complete === true;
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
      const checkedAt = Date.parse(result.checked_at);
      if (checkedMeta && checked) {
        checkedMeta.hidden = !Number.isFinite(checkedAt);
        if (Number.isFinite(checkedAt)) {
          checked.dateTime = result.checked_at;
          checked.textContent = publicationTime.format(new Date(checkedAt));
        }
      }
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
