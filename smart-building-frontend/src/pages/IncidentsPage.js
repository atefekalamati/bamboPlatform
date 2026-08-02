import { sessionStore } from "../app/sessionStore.js";
import { Modal } from "../components/Modal.js";
import { Pagination } from "../components/Pagination.js";
import { INCIDENT_LABELS, incidentSlaState, isIncidentOverdue } from "../features/incidents/incidentConstants.js";
import { incidentService } from "../services/incidentService.js";
import { pilotService } from "../services/pilotService.js";
import { formatPersianDateTime } from "../utils/dateFormatter.js";

const PAGE_SIZE = 20;
const node = (tag, className = "", text = "") => { const element = document.createElement(tag); element.className = className; element.textContent = text; return element; };
const select = (labelText, values) => { const label = node("label", "filter-field"); const control = document.createElement("select"); control.className = "filter-field__control"; values.forEach(([value, text]) => control.append(new Option(text, value))); label.append(node("span", "filter-field__label", labelText), control); return { label, control }; };

const IncidentCard = ({ incident }) => {
  const card = node("article", `incident-card severity-${incident.severity}`);
  const header = node("header", "incident-card__header");
  header.append(node("a", "incident-card__code", incident.code), node("span", `incident-badge severity-${incident.severity}`, `شدت: ${INCIDENT_LABELS.severity[incident.severity]}`));
  header.querySelector("a").href = `#/incidents/${incident.id}`;
  const meta = node("dl", "incident-card__meta");
  [["پرونده", incident.pilotCode], ["مرحله", String(incident.stageNumber)], ["نوع", INCIDENT_LABELS.type[incident.incidentType]], ["وضعیت", INCIDENT_LABELS.status[incident.status]], ["SLA", incidentSlaState(incident).label], ["زمان وقوع", formatPersianDateTime(incident.occurredAt)]].forEach(([key, value]) => { const row = node("div"); row.append(node("dt", "", key), node("dd", "", value)); meta.append(row); });
  card.append(header, node("p", "incident-card__description", incident.description), meta);
  const actions = node("div", "incident-card__actions"); const detail = node("a", "button button--ghost", "مشاهده و پیگیری"); detail.href = `#/incidents/${incident.id}`; const stage = node("a", "button-link", `رفتن به مرحله ${incident.stageNumber}`); stage.href = `#/pilots/${incident.pilotId}/stages/${incident.stageNumber}`; actions.append(detail, stage); card.append(actions);
  return card;
};

export const IncidentsPage = () => {
  const permissions = sessionStore.getCurrentUser()?.permissions ?? [];
  const canRead = permissions.includes("incidents.read") && permissions.includes("pilots.read");
  const canManage = permissions.includes("incidents.manage");
  const page = node("div", "page incidents-page");
  if (!canRead) { page.append(node("p", "error-state__message", "برای مشاهده رخدادها دسترسی لازم را ندارید.")); return page; }
  const heading = node("header", "page-heading"); heading.append(node("p", "page-heading__eyebrow", "کنترل کیفیت و اقدام اصلاحی"), node("h1", "page-heading__title", "رخدادها"), node("p", "page-heading__description", "رخدادهای عملیاتی، فنی، ایمنی و مشتری را در پرونده‌های قابل دسترس خود پیگیری کنید."));
  const actions = node("div", "incidents-heading-actions"); const create = node("button", "button button--primary", "ثبت رخداد جدید"); create.type = "button"; create.hidden = !canManage; actions.append(create); heading.append(actions);
  const summary = node("section", "incident-summary"); const filters = node("div", "incident-filters card"); const search = document.createElement("input"); search.type = "search"; search.className = "filter-field__control"; search.placeholder = "کد، پرونده یا شرح رخداد";
  const searchLabel = node("label", "filter-field"); searchLabel.append(node("span", "filter-field__label", "جست‌وجو"), search);
  const status = select("وضعیت", [["", "همه"], ...Object.entries(INCIDENT_LABELS.status)]); const severity = select("شدت", [["", "همه"], ...Object.entries(INCIDENT_LABELS.severity)]); const type = select("نوع", [["", "همه"], ...Object.entries(INCIDENT_LABELS.type)]); filters.append(searchLabel, status.label, severity.label, type.label);
  const content = node("section", "incident-list"); page.append(heading, summary, filters, content);
  let incidents = []; let pilots = []; let pageNumber = 1; let quickFilter = "";
  const render = () => {
    const now = Date.now();
    const counts = { total: incidents.length, open: incidents.filter((item) => item.status === "open").length, critical: incidents.filter((item) => item.severity === "critical").length, important: incidents.filter((item) => item.severity === "important").length, overdue: incidents.filter((item) => isIncidentOverdue(item, now)).length, closed: incidents.filter((item) => item.status === "closed").length };
    summary.replaceChildren();
    [["total", "همه رخدادها", "◎"], ["open", "باز", "◌"], ["critical", "بحرانی", "!"], ["important", "مهم", "▲"], ["overdue", "گذشته از مهلت", "◷"], ["closed", "بسته‌شده", "✓"]].forEach(([code, label, icon]) => { const button = node("button", `incident-summary__card${quickFilter === code ? " is-active" : ""}`); button.type = "button"; button.append(node("span", "incident-summary__icon", icon), node("strong", "", String(counts[code])), node("span", "", label)); button.addEventListener("click", () => { quickFilter = quickFilter === code ? "" : code; pageNumber = 1; render(); }); summary.append(button); });
    const query = search.value.trim().toLocaleLowerCase("fa");
    const filtered = incidents.filter((item) => (!query || `${item.code} ${item.pilotCode} ${item.description}`.toLocaleLowerCase("fa").includes(query)) && (!status.control.value || item.status === status.control.value) && (!severity.control.value || item.severity === severity.control.value) && (!type.control.value || item.incidentType === type.control.value) && (!quickFilter || quickFilter === "total" || (quickFilter === "overdue" ? isIncidentOverdue(item) : quickFilter === "critical" || quickFilter === "important" ? item.severity === quickFilter : item.status === quickFilter)));
    const totalPages = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE)); pageNumber = Math.min(pageNumber, totalPages); const visible = filtered.slice((pageNumber - 1) * PAGE_SIZE, pageNumber * PAGE_SIZE);
    if (!visible.length) { content.replaceChildren(node("p", "notification-empty card", "هیچ رخدادی با این فیلتر پیدا نشد.")); return; }
    const list = node("div", "incident-card-list"); visible.forEach((item) => list.append(IncidentCard({ incident: item })));
    content.replaceChildren(node("p", "results-count", `${filtered.length} رخداد`), list);
    if (totalPages > 1) content.append(Pagination({ activePage: pageNumber, totalPages, onPageChange: (nextPage) => { pageNumber = nextPage; render(); } }));
  };
  const load = async () => { content.replaceChildren(node("p", "loading-state", "در حال دریافت رخدادهای پرونده‌ها…")); try { pilots = await pilotService.getPilots(); const groups = await Promise.all(pilots.map(async (pilot) => (await incidentService.getPilotIncidents(pilot.id)).map((incident) => ({ ...incident, pilotCode: pilot.code, pilotName: pilot.displayName })))); incidents = groups.flat().sort((a, b) => new Date(b.occurredAt) - new Date(a.occurredAt)); render(); } catch (error) { const retry = node("button", "button button--primary", "تلاش مجدد"); retry.type = "button"; retry.addEventListener("click", load); content.replaceChildren(node("p", "error-state__message", error.message ?? "دریافت رخدادها انجام نشد."), retry); } };
  [search, status.control, severity.control, type.control].forEach((control) => control.addEventListener(control === search ? "input" : "change", () => { pageNumber = 1; render(); }));
  create.addEventListener("click", () => {
    const form = node("form", "incident-pilot-picker"); const picker = document.createElement("select"); picker.className = "form-field__input"; pilots.forEach((pilot) => picker.append(new Option(`${pilot.code} — ${pilot.displayName}`, String(pilot.id))));
    const label = node("label", "form-field"); label.append(node("span", "form-field__label", "پرونده پایلوت"), picker); const submit = node("button", "button button--primary", "ادامه و ثبت رخداد"); submit.type = "submit"; form.append(label, submit);
    let modal; form.addEventListener("submit", (event) => { event.preventDefault(); modal.close(); window.location.hash = `#/pilots/${picker.value}/incidents/new`; }); modal = Modal({ title: "انتخاب پرونده رخداد", content: form, triggerElement: create, centered: true });
  });
  load(); return page;
};
