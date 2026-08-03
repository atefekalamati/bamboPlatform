import { formatPersianDateTime } from "../utils/dateFormatter.js";
import { translateActionTitle, translateAuditAction, translateDisplayValue } from "../utils/displayText.js";

const node = (tag, className = "", text = "") => { const item = document.createElement(tag); item.className = className; item.textContent = text; return item; };
export const label = (value) => translateDisplayValue(value);

export const DashboardKpiCard = ({ label: title, value, tone = "default" }) => {
  const card = node("article", `dashboard-kpi dashboard-kpi--${tone}`);
  card.append(node("span", "dashboard-kpi__label", title), node("strong", "dashboard-kpi__value", String(value ?? 0)));
  return card;
};

export const DashboardFilters = ({ values, onChange }) => {
  const form = node("form", "dashboard-filters dashboard-panel");
  const controls = [
    ["q", "جست‌وجو", "search", "کد، پروژه یا مالک"], ["status", "وضعیت", "select", [["", "همه وضعیت‌ها"], ["open", "باز"], ["submitted", "ارسال‌شده"], ["approved", "تأییدشده"], ["needs_revision", "نیازمند اصلاح"], ["contract", "قرارداد"]]],
    ["stage", "مرحله", "select", [["", "همه مراحل"], ...Array.from({ length: 19 }, (_, index) => [String(index + 1), `مرحله ${index + 1}`])]],
    ["sla", "SLA", "select", [["", "همه"], ["on_track", "در مسیر"], ["at_risk", "نزدیک موعد"], ["overdue", "معوق"], ["not_applicable", "بدون SLA"]]],
    ["sort", "مرتب‌سازی", "select", [["updated", "آخرین تغییر"], ["stage", "مرحله"], ["sla", "SLA"], ["code", "کد پرونده"]]],
  ];
  controls.forEach(([name, title, type, data]) => {
    const wrapper = node("label", "dashboard-filter"); wrapper.append(node("span", "dashboard-filter__label", title));
    const control = document.createElement(type === "select" ? "select" : "input"); control.name = name; control.className = "dashboard-filter__control";
    if (type === "search") { control.type = "search"; control.placeholder = data; }
    else data.forEach(([value, text]) => control.append(new Option(text, value)));
    control.value = values[name] ?? ""; wrapper.append(control); form.append(wrapper);
  });
  const reset = node("button", "button button--ghost", "پاک‌کردن فیلترها"); reset.type = "button"; reset.addEventListener("click", () => onChange({ page: 1, q: "", status: "", stage: "", sla: "", sort: "updated" })); form.append(reset);
  let timer; form.addEventListener("input", () => { window.clearTimeout(timer); timer = window.setTimeout(() => onChange(Object.fromEntries(new FormData(form))), 350); });
  form.addEventListener("change", () => onChange(Object.fromEntries(new FormData(form))));
  return form;
};

export const PilotList = ({ response, onPage }) => {
  const section = node("section", "dashboard-panel dashboard-pilots"); section.append(node("h2", "dashboard-panel__title", "پرونده‌های پایلوت"));
  if (!response.items.length) { section.append(node("p", "dashboard-state", response.state === "NO_ACCESS" ? "در حال حاضر پرونده‌ای به شما تخصیص داده نشده است" : "هنوز پرونده‌ای ثبت نشده است")); return section; }
  const viewport = node("div", "dashboard-table-wrap"); const table = node("table", "dashboard-table");
  const head = document.createElement("thead"); const hr = document.createElement("tr"); ["پرونده و پروژه", "مرحله", "پیشرفت", "مسئول", "اقدام بعدی", "SLA", "رخداد", "Gate", "نتیجه", "آخرین تغییر"].forEach((text) => hr.append(node("th", "", text))); head.append(hr);
  const body = document.createElement("tbody"); response.items.forEach((item) => {
    const row = document.createElement("tr"); const pilot = node("td"); const link = node("a", "dashboard-table__link", item.pilot_code); link.href = `#/pilots/${item.id}`; pilot.append(link, node("small", "", `${item.project}${item.owner_company ? ` · ${item.owner_company}` : ""}`));
    const progress = node("td"); const meter = document.createElement("progress"); meter.max = 100; meter.value = item.progress_percent; progress.append(meter, node("small", "", `${item.progress_percent}٪`));
    const incident = item.critical_incidents ? `${item.open_incidents} باز · ${item.critical_incidents} بحرانی` : `${item.open_incidents} باز`;
    const cells = [pilot, node("td", "", `${item.current_stage} از ۱۹ · ${label(item.stage_status)}`), progress, node("td", "", item.current_assignee ?? "تخصیص‌نیافته"), node("td", "", label(item.next_action)), node("td", `dashboard-badge dashboard-badge--${item.sla_status}`, `${label(item.sla_status)}${item.due_at ? ` · ${formatPersianDateTime(item.due_at)}` : ""}`), node("td", item.critical_incidents ? "dashboard-danger" : "", incident), node("td", "", translateDisplayValue(item.current_gate)), node("td", "", label(item.final_outcome ?? item.commercial_status)), node("td", "", formatPersianDateTime(item.last_updated_at))];
    ["پرونده و پروژه", "مرحله", "پیشرفت", "مسئول", "اقدام بعدی", "SLA", "رخداد", "Gate", "نتیجه", "آخرین تغییر"].forEach((title, index) => { cells[index].dataset.label = title; row.append(cells[index]); }); body.append(row);
  }); table.append(head, body); viewport.append(table); section.append(viewport);
  const p = response.pagination; if (p?.total_pages > 1) { const nav = node("nav", "dashboard-pagination"); const prev = node("button", "button button--ghost", "قبلی"); const next = node("button", "button button--ghost", "بعدی"); prev.disabled = p.page <= 1; next.disabled = p.page >= p.total_pages; prev.onclick = () => onPage(p.page - 1); next.onclick = () => onPage(p.page + 1); nav.append(prev, node("span", "", `صفحه ${p.page} از ${p.total_pages}`), next); section.append(nav); }
  return section;
};

export const MyActions = ({ response }) => {
  const section = node("section", "dashboard-panel dashboard-actions"); section.append(node("h2", "dashboard-panel__title", "اقدامات موردنیاز من"));
  if (!response.items.length) { section.append(node("p", "dashboard-state", "در حال حاضر اقدام بازی برای شما ثبت نشده است.")); return section; }
  const list = node("ul", "dashboard-action-list"); response.items.slice(0, 8).forEach((item) => { const li = node("li", `dashboard-action dashboard-action--${item.priority.toLowerCase()}`); const link = node("a", "dashboard-action__link", translateActionTitle(item.title)); const target = item.entity_type === "incident" ? `#/incidents/${item.entity_id}` : item.entity_type === "stage" ? `#/pilots/${item.pilot_id}/stages/${item.action_url?.split("/").at(-1)}` : `#/pilots/${item.pilot_id}`; link.href = target; li.append(link, node("span", "", `${translateDisplayValue(item.priority, "عادی")}${item.due_at ? ` · ${formatPersianDateTime(item.due_at)}` : ""}`)); list.append(li); }); section.append(list); return section;
};

export const SummaryWidget = ({ title, items, keyName, valueName = "count" }) => {
  const section = node("section", "dashboard-panel dashboard-widget"); section.append(node("h2", "dashboard-panel__title", title));
  const list = node("dl", "dashboard-widget__list"); items.forEach((item) => { const row = node("div", "dashboard-widget__row"); const rawValue = item[valueName] ?? item.total ?? 0; row.append(node("dt", "", label(item[keyName])), node("dd", "", typeof rawValue === "string" ? translateDisplayValue(rawValue, "ثبت‌شده") : String(rawValue))); list.append(row); }); section.append(list); return section;
};

export const RecentActivities = ({ response }) => SummaryWidget({ title: "فعالیت‌های اخیر", items: response.items.slice(0, 8).map((item) => ({ ...item, action: `${translateAuditAction(item.action)} · ${formatPersianDateTime(item.created_at)}` })), keyName: "action", valueName: "pilot_id" });
