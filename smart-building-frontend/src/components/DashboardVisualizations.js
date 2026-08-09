import { getStageTitle } from "../constants/stageCatalog.js";
import { translateDisplayValue } from "../utils/displayText.js";

const SVG_NS = "http://www.w3.org/2000/svg";
const node = (tag, className = "", text = "") => { const item = document.createElement(tag); item.className = className; item.textContent = text; return item; };
const svgNode = (tag, attributes = {}) => { const item = document.createElementNS(SVG_NS, tag); Object.entries(attributes).forEach(([key, value]) => item.setAttribute(key, value)); return item; };
const safeNumber = (value) => Math.max(0, Number(value) || 0);

export const DASHBOARD_METRICS = Object.freeze([
  ["active", "فعال"], ["waiting_action", "در انتظار اقدام"], ["sla_at_risk", "نزدیک SLA"], ["sla_overdue", "معوق"],
  ["open_critical_incidents", "رخداد بحرانی باز"], ["completed", "تکمیل‌شده"], ["contracted", "قراردادشده"],
]);

export const dashboardMetricValues = (summary = {}) => DASHBOARD_METRICS.map(([key, label], index) => ({ key, label, value: safeNumber(summary[key]), tone: index + 1 }));

export const processCompletionPercent = (summary = {}) => {
  const total = safeNumber(summary.total_pilots);
  const completed = Math.min(total, safeNumber(summary.completed));
  return total ? Math.round((completed / total) * 100) : 0;
};

export const ProcessHealthChart = ({ summary = {} }) => {
  const section = node("section", "dashboard-panel dashboard-health");
  const header = node("header", "dashboard-panel__header"); const heading = node("div");
  heading.append(node("h2", "dashboard-panel__title", "سلامت فرایند"), node("p", "dashboard-panel__description", "خلاصه وضعیت عملیاتی پرونده‌ها")); header.append(heading); section.append(header);
  const metrics = dashboardMetricValues(summary);
  const totalPilots = safeNumber(summary.total_pilots);
  const completionPercent = processCompletionPercent(summary);
  const chartArea = node("div", "dashboard-health__body"); const figure = node("figure", "dashboard-health__figure");
  const svg = svgNode("svg", { viewBox: "0 0 220 220", role: "img", "aria-labelledby": "dashboard-health-title dashboard-health-desc" });
  const title = svgNode("title", { id: "dashboard-health-title" }); title.textContent = "نمودار شاخص‌های وضعیت پرونده‌ها";
  const desc = svgNode("desc", { id: "dashboard-health-desc" });
  desc.textContent = totalPilots
    ? `${completionPercent} درصد پرونده‌ها تکمیل شده‌اند؛ سایر اعداد شاخص‌های مستقل هستند.`
    : "هنوز پرونده‌ای در محدوده دسترسی ثبت نشده است";
  svg.append(title, desc, svgNode("circle", { cx: "110", cy: "110", r: "78", class: "dashboard-health__ring-base" }));
  if (totalPilots > 0 && completionPercent > 0) {
    const circle = svgNode("circle", {
      cx: "110",
      cy: "110",
      r: "78",
      pathLength: "100",
      class: "dashboard-health__segment dashboard-health__segment--1",
      "stroke-dasharray": `${completionPercent} ${100 - completionPercent}`,
    });
    const tooltip = svgNode("title");
    tooltip.textContent = `تکمیل‌شده: ${safeNumber(summary.completed)} از ${totalPilots}`;
    circle.append(tooltip);
    svg.append(circle);
  }
  const center = svgNode("text", { x: "110", y: "105", class: "dashboard-health__total", "text-anchor": "middle" }); center.textContent = String(totalPilots);
  const centerLabel = svgNode("text", { x: "110", y: "130", class: "dashboard-health__total-label", "text-anchor": "middle" }); centerLabel.textContent = "کل پرونده‌ها"; svg.append(center, centerLabel); figure.append(svg);
  const legend = node("ul", "dashboard-health__legend");
  metrics.forEach((metric) => { const item = node("li", "dashboard-health__legend-item"); const marker = node("span", `dashboard-health__marker dashboard-health__marker--${metric.tone}`); marker.setAttribute("aria-hidden", "true"); item.title = `${metric.label}: ${metric.value}`; item.append(marker, node("span", "dashboard-health__legend-label", metric.label), node("strong", "dashboard-health__legend-value", String(metric.value))); legend.append(item); });
  chartArea.append(figure, legend);
  section.append(chartArea);
  section.append(node("p", "dashboard-health__note", "حلقه فقط نسبت پرونده‌های تکمیل‌شده به کل را نشان می‌دهد؛ شاخص‌های کنار نمودار ممکن است با هم هم‌پوشانی داشته باشند."));
  if (!totalPilots) section.append(node("p", "dashboard-health__empty", "هنوز پرونده‌ای در محدوده دسترسی ثبت نشده است."));
  return section;
};

const STAGE_STATUS_CLASSES = Object.freeze({ approved: "complete", submitted: "waiting", open: "current", needs_revision: "revision", locked: "locked" });
export const stageProgressPercent = (stages = []) => Math.round((stages.filter(({ status }) => status === "approved").length / 19) * 100);
export const canOpenStageFromDashboard = (stage) => stage?.status === "open";

export const ProjectStageJourney = ({ pilots = [], selectedPilotId, onSelect, onRetry }) => {
  const section = node("section", "dashboard-panel dashboard-stage-journey"); const header = node("header", "dashboard-stage-journey__header");
  const heading = node("div"); heading.append(node("h2", "dashboard-panel__title", "وضعیت مراحل پروژه"), node("p", "dashboard-panel__description", "وضعیت ۱۹ مرحله پروژه انتخاب‌شده"));
  const label = node("label", "dashboard-stage-journey__selector"); label.append(node("span", "sr-only", "انتخاب پروژه"));
  const select = document.createElement("select"); select.className = "dashboard-filter__control"; select.setAttribute("aria-label", "انتخاب پروژه"); pilots.forEach((pilot) => select.append(new Option(`${pilot.code} — ${pilot.displayName}`, String(pilot.id)))); if (selectedPilotId != null) select.value = String(selectedPilotId); select.addEventListener("change", () => onSelect?.(select.value)); label.append(select); header.append(heading, label); section.append(header);
  const body = node("div", "dashboard-stage-journey__content"); section.append(body);
  const renderState = (message, kind = "loading") => { const state = node("div", `dashboard-state dashboard-stage-journey__state dashboard-state--${kind}`, message); if (kind === "error") { const retry = node("button", "button button--primary", "تلاش مجدد"); retry.type = "button"; retry.addEventListener("click", onRetry); state.append(retry); } body.replaceChildren(state); };
  section.showLoading = () => renderState("در حال دریافت وضعیت مراحل پروژه…"); section.showError = () => renderState("دریافت وضعیت مراحل پروژه انجام نشد.", "error"); section.showEmpty = () => renderState("اطلاعات مراحل این پروژه در دسترس نیست.", "empty");
  section.renderPilot = (pilot) => {
    const stages = Array.isArray(pilot?.stages) ? pilot.stages : []; if (!stages.length) { section.showEmpty(); return; }
    const progress = stageProgressPercent(stages); const summary = node("div", "dashboard-stage-journey__summary"); summary.append(node("strong", "", pilot.displayName), node("span", "", `${progress}٪ تکمیل‌شده`));
    const meter = document.createElement("progress"); meter.max = 100; meter.value = progress; meter.setAttribute("aria-label", `پیشرفت کلی ${pilot.displayName}`); summary.append(meter);
    const list = node("ol", "dashboard-stage-journey__list");
    Array.from({ length: 19 }, (_, index) => index + 1).forEach((number) => {
      const stage = stages.find((item) => Number(item.number) === number) ?? { number, status: "locked" };
      const statusClass = STAGE_STATUS_CLASSES[stage.status] ?? "locked";
      const title = getStageTitle(number, stage.title);
      const statusLabel = translateDisplayValue(stage.status, "قفل‌شده");
      const item = node("li", `dashboard-stage-node dashboard-stage-node--${statusClass}`);
      const canOpen = canOpenStageFromDashboard(stage);
      const content = canOpen ? node("a", "dashboard-stage-node__link") : node("div", "dashboard-stage-node__content");
      item.title = `${title} — ${statusLabel}`;
      content.append(node("span", "dashboard-stage-node__number", String(number)), node("span", "dashboard-stage-node__title", title), node("span", "dashboard-stage-node__status", statusLabel));
      if (canOpen) {
        content.href = `#/pilots/${pilot.id}/stages/${number}`;
        content.setAttribute("aria-label", `ورود به مرحله ${number}: ${title}`);
        item.title = `ورود به ${title}`;
      }
      item.append(content); list.append(item);
    });
    body.replaceChildren(summary, list);
  };
  if (!pilots.length) section.showEmpty(); else section.showLoading(); return section;
};
