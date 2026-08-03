import { formatPersianDateTime } from "../utils/dateFormatter.js";

export const el = (tag, className = "", text = "") => {
  const item = document.createElement(tag);
  item.className = className;
  item.textContent = text;
  return item;
};

export const REPORT_TABS = [
  ["#/reports", "خلاصه مدیریتی"], ["#/reports/pilots", "پیشرفت پرونده‌ها"],
  ["#/reports/actions", "اقدامات"], ["#/reports/kpis", "KPI و SLA"],
  ["#/reports/incidents", "رخدادها"],
];

export const ReportTabs = (active) => {
  const nav = el("nav", "report-tabs");
  nav.setAttribute("aria-label", "بخش‌های گزارش مدیریتی");
  REPORT_TABS.forEach(([href, label]) => {
    const link = el("a", `report-tabs__link${href === active ? " is-active" : ""}`, label);
    link.href = href;
    if (href === active) link.setAttribute("aria-current", "page");
    nav.append(link);
  });
  return nav;
};

const field = (label, name, options, type = "select") => {
  const wrapper = el("label", "report-filter");
  const control = document.createElement(type === "select" ? "select" : "input");
  control.className = "report-filter__control";
  control.name = name;
  if (type !== "select") control.type = type;
  (options ?? []).forEach(([value, text]) => control.append(new Option(text, value)));
  wrapper.append(el("span", "report-filter__label", label), control);
  return { wrapper, control };
};

export const readHashQuery = () => Object.fromEntries(new URLSearchParams((window.location.hash.split("?")[1] ?? "")));

export const writeHashQuery = (route, values) => {
  const query = new URLSearchParams();
  Object.entries(values).forEach(([key, value]) => {
    if (value !== "" && value !== null && value !== undefined && key !== "page") query.set(key, value);
  });
  if (Number(values.page) > 1) query.set("page", values.page);
  const next = `${route}${query.size ? `?${query}` : ""}`;
  if (window.location.hash !== next) window.location.hash = next;
};

export const ReportFilters = ({ route, extra = [], onApply }) => {
  const form = el("form", "report-filters dashboard-panel");
  const initial = readHashQuery();
  const definitions = [
    ["جست‌وجو", "q", null, "search"],
    ["وضعیت پرونده", "pilot_status", [["", "همه"], ["candidate", "نامزد"], ["waiting_documents", "در انتظار مدارک"], ["operations", "عملیات"], ["evaluating", "در ارزیابی"], ["proposal_sent", "پیشنهاد ارسال‌شده"], ["converted", "قراردادشده"], ["closed", "بسته‌شده"]]],
    ["مرحله", "stage", [["", "همه"], ...Array.from({ length: 19 }, (_, index) => [String(index + 1), `مرحله ${index + 1}`])]],
    ["Gate", "gate", [["", "همه"], ...[1,2,3,4,5].map((n) => [`G${n}`, `G${n}`])]],
    ["SLA", "sla", [["", "همه"], ["on_track", "در مسیر"], ["at_risk", "نزدیک مهلت"], ["overdue", "معوق"], ["not_applicable", "نامرتبط"]]],
    ["از تاریخ", "date_from", null, "datetime-local"], ["تا تاریخ", "date_to", null, "datetime-local"],
    ...extra,
  ];
  const controls = {};
  definitions.forEach(([label, name, options, type]) => {
    const item = field(label, name, options, type);
    item.control.value = initial[name] ?? "";
    controls[name] = item.control;
    form.append(item.wrapper);
  });
  const actions = el("div", "report-filter-actions");
  const apply = el("button", "button button--primary", "اعمال فیلتر"); apply.type = "submit";
  const reset = el("button", "button button--ghost", "پاک‌کردن"); reset.type = "button";
  actions.append(apply, reset); form.append(actions);
  const values = () => ({ ...Object.fromEntries(Object.entries(controls).map(([key, control]) => [key, control.value])), page: 1 });
  form.addEventListener("submit", (event) => { event.preventDefault(); const data = values(); writeHashQuery(route, data); onApply?.(data); });
  reset.addEventListener("click", () => { Object.values(controls).forEach((control) => { control.value = ""; }); writeHashQuery(route, { page: 1 }); onApply?.({ page: 1 }); });
  let timer;
  controls.q?.addEventListener("input", () => { clearTimeout(timer); timer = setTimeout(() => form.requestSubmit(), 350); });
  return form;
};

export const ReportState = ({ kind, message, retry, traceId }) => {
  const box = el("section", `report-state report-state--${kind}`);
  if (kind === "loading") {
    box.setAttribute("aria-label", "در حال بارگذاری");
    for (let i = 0; i < 4; i += 1) box.append(el("span", "report-skeleton"));
    return box;
  }
  box.append(el("h2", "report-state__title", kind === "no-access" ? "دسترسی محدود" : kind === "empty" ? "داده‌ای ثبت نشده است" : "دریافت گزارش انجام نشد"), el("p", "", message));
  if (traceId) box.append(el("small", "", `شناسه پیگیری: ${traceId}`));
  if (retry) { const button = el("button", "button button--primary", "تلاش مجدد"); button.type = "button"; button.addEventListener("click", retry); box.append(button); }
  return box;
};

export const statusLabel = (value) => ({
  open:"باز", submitted:"ارسال‌شده", approved:"تأییدشده", passed:"تأییدشده", locked:"قفل",
  needs_revision:"نیازمند اصلاح", completed:"تکمیل‌شده", closed:"بسته‌شده", critical:"بحرانی",
  important:"مهم", normal:"عادی", on_track:"در مسیر", at_risk:"نزدیک مهلت", overdue:"معوق",
  good:"مطلوب", needs_attention:"نیازمند توجه", insufficient_data:"داده ناکافی",
  candidate:"نامزد", waiting_documents:"در انتظار مدارک", ready_for_operation:"آماده عملیات",
  operations:"در عملیات", ready_for_customer:"آماده مشتری", evaluating:"در ارزیابی",
  proposal_sent:"پیشنهاد ارسال‌شده", converted:"قراردادشده", stopped:"متوقف‌شده",
  stage:"مرحله", incident:"رخداد", mission:"مأموریت", proposal:"پیشنهاد تجاری",
  high:"زیاد", medium:"متوسط", low:"کم",
}[value] ?? value ?? "—");

export const dateText = (value) => value ? formatPersianDateTime(value) : "ثبت نشده";

export const Pagination = ({ pagination, route, filters }) => {
  if (!pagination || pagination.total_pages <= 1) return document.createDocumentFragment();
  const nav = el("nav", "report-pagination"); nav.setAttribute("aria-label", "صفحه‌بندی گزارش");
  const previous = el("button", "button button--ghost", "قبلی"); previous.disabled = pagination.page <= 1;
  const next = el("button", "button button--ghost", "بعدی"); next.disabled = pagination.page >= pagination.total_pages;
  previous.addEventListener("click", () => writeHashQuery(route, { ...filters, page: pagination.page - 1 }));
  next.addEventListener("click", () => writeHashQuery(route, { ...filters, page: pagination.page + 1 }));
  nav.append(previous, el("span", "", `صفحه ${pagination.page} از ${pagination.total_pages}`), next); return nav;
};

export const responseState = (payload, retry) => {
  if (payload?.state === "NO_ACCESS") return ReportState({ kind: "no-access", message: "در حال حاضر پرونده‌ای در محدوده دسترسی شما نیست." });
  if (payload?.state === "NO_DATA") return ReportState({ kind: "empty", message: "هنوز داده‌ای برای این گزارش ثبت نشده است." });
  if (payload?.state === "PARTIAL_DATA") return el("div", "report-partial", "بخشی از داده‌ها کامل نیست؛ مقادیر موجود نمایش داده شده‌اند.");
  return null;
};

