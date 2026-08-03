import { sessionStore } from "../app/sessionStore.js";
import {
  DashboardFilters, DashboardKpiCard, MyActions, PilotList, RecentActivities, SummaryWidget,
} from "../components/DashboardComponents.js";
import { PowerBIReport } from "../components/PowerBIReport.js";
import { dashboardService } from "../services/dashboardService.js";
import { notificationService } from "../services/notificationService.js";
import { formatPersianDateTime } from "../utils/dateFormatter.js";

const node = (tag, className = "", text = "") => { const item = document.createElement(tag); item.className = className; item.textContent = text; return item; };
const has = (permissions, permission) => permissions.includes(permission);

const readFilters = () => {
  const params = new URLSearchParams(window.location.search);
  return { page: Math.max(1, Number(params.get("page")) || 1), page_size: 20, q: params.get("q") ?? "", status: params.get("status") ?? "", stage: params.get("stage") ?? "", sla: params.get("sla") ?? "", sort: params.get("sort") ?? "updated" };
};

const writeFilters = (filters) => {
  const query = new URLSearchParams();
  Object.entries(filters).forEach(([key, value]) => { if (value && key !== "page_size" && !(key === "page" && Number(value) === 1)) query.set(key, value); });
  const suffix = query.toString();
  window.history.replaceState(null, "", `${window.location.pathname}${suffix ? `?${suffix}` : ""}${window.location.hash || "#/"}`);
};

const Skeleton = () => {
  const area = node("div", "dashboard-skeleton");
  for (let index = 0; index < 8; index += 1) area.append(node("div", "dashboard-skeleton__item"));
  area.setAttribute("aria-label", "در حال بارگذاری نمای کلی"); return area;
};

const QuickActions = ({ permissions }) => {
  const definitions = [
    ["pilots.create", "ایجاد پرونده", "#/pilots"], ["missions.create", "ایجاد مأموریت", "#/pilots"],
    ["incidents.create", "ثبت رخداد", "#/incidents"], ["dashboard.read", "کارهای من", "#dashboard-actions"],
    ["reports.sla", "پرونده‌های معوق", "?sla=overdue#/"], ["reports.powerbi", "گزارش مدیریتی", "#powerbi-report"],
    ["users.read", "کاربران", "#/users"], ["roles.read", "نقش‌ها و دسترسی‌ها", "#/roles"],
  ];
  const section = node("section", "dashboard-quick-actions"); section.setAttribute("aria-label", "دسترسی سریع");
  definitions.filter(([permission]) => has(permissions, permission)).forEach(([, title, href]) => {
    if (href === "#dashboard-actions" || href === "#powerbi-report") {
      const button = node("button", "button button--ghost", title); button.type = "button";
      button.addEventListener("click", () => document.querySelector(href)?.scrollIntoView({ behavior: "smooth", block: "start" })); section.append(button); return;
    }
    const link = node("a", "button button--ghost", title); link.href = href; section.append(link);
  });
  return section;
};

const widgetFor = (kind, response) => {
  const definitions = {
    stages: ["وضعیت ۱۹ مرحله", "stage", "total"], gates: ["وضعیت Gateها", "gate", "blocked"],
    missions: ["ماموریت‌ها", "status", "count"], incidents: ["رخدادهای مهم", "severity", "open"],
    sla: ["هشدارهای SLA", "status", "count"], forms: ["وضعیت فرم‌های F01 تا F05", "form", "completed"],
    commercial: ["مسیر تجاری", "outcome", "count"],
  };
  const [title, keyName, valueName] = definitions[kind];
  return SummaryWidget({ title, items: response.items, keyName, valueName });
};

export const DashboardPage = () => {
  const page = node("div", "page dashboard-page");
  const permissions = sessionStore.getCurrentUser()?.permissions ?? [];
  const heading = node("header", "page-heading dashboard-heading");
  const headingText = node("div");
  headingText.append(node("p", "page-heading__eyebrow", "BAMBO Pilot"), node("h1", "page-heading__title", "نمای کلی سامانه مدیریت فرایند پایلوت"), node("p", "page-heading__description", "تصویر عملیاتی پرونده‌ها، اقدام‌های لازم، SLA و مسیر تجاری بر اساس دسترسی شما"));
  const updated = node("time", "dashboard-heading__updated", ""); heading.append(headingText, updated);
  const content = node("div", "dashboard-content"); page.append(heading, QuickActions({ permissions }), content);

  if (!has(permissions, "dashboard.read")) {
    content.append(node("section", "dashboard-panel dashboard-state dashboard-state--no-access", "برای مشاهده نمای کلی دسترسی dashboard.read لازم است."));
    return page;
  }

  let filters = readFilters(); let pilotController = null;
  const renderPilots = async (container) => {
    pilotController?.abort(); pilotController = new AbortController();
    container.replaceChildren(Skeleton());
    try {
      const response = await dashboardService.getPilots(filters, { signal: pilotController.signal });
      container.replaceChildren(PilotList({ response, onPage: (pageNumber) => { filters.page = pageNumber; writeFilters(filters); renderPilots(container); } }));
    } catch (error) {
      if (error.name === "AbortError") return;
      const retry = node("button", "button button--primary", "تلاش مجدد"); retry.type = "button"; retry.onclick = () => renderPilots(container);
      const state = node("section", "dashboard-panel dashboard-state dashboard-state--error", error.status === 403 ? "به فهرست پرونده‌های این نما دسترسی ندارید." : "دریافت فهرست پرونده‌ها انجام نشد."); state.append(retry); container.replaceChildren(state);
    }
  };

  const load = async () => {
    content.replaceChildren(Skeleton());
    try {
      const [summary, actions, stages, gates, missions, incidents, sla, forms, commercial, activities] = await Promise.all([
        dashboardService.getSummary(), dashboardService.getMyActions(), dashboardService.getStageSummary(), dashboardService.getGateSummary(), dashboardService.getMissionSummary(), dashboardService.getIncidentSummary(), dashboardService.getSlaSummary(), dashboardService.getFormsSummary(), dashboardService.getCommercialSummary(), dashboardService.getRecentActivities(),
      ]);
      updated.textContent = `آخرین بروزرسانی: ${formatPersianDateTime(summary.generated_at)}`;
      content.replaceChildren();
      if (summary.state === "NO_ACCESS") { content.append(node("section", "dashboard-panel dashboard-state dashboard-state--no-access", "در حال حاضر پرونده‌ای به شما تخصیص داده نشده است")); return; }
      if (summary.state === "NO_DATA") {
        const empty = node("section", "dashboard-panel dashboard-state", "هنوز پرونده‌ای ثبت نشده است");
        if (has(permissions, "pilots.create")) { const create = node("a", "button button--primary", "ایجاد اولین پرونده"); create.href = "#/pilots"; empty.append(create); } content.append(empty); return;
      }
      const kpis = node("section", "dashboard-kpis"); const s = summary.summary;
      [["کل پرونده‌ها", s.total_pilots], ["فعال", s.active], ["در انتظار اقدام", s.waiting_action, "warning"], ["نزدیک SLA", s.sla_at_risk, "warning"], ["معوق", s.sla_overdue, "danger"], ["رخداد بحرانی باز", s.open_critical_incidents, "danger"], ["تکمیل‌شده", s.completed, "success"], ["قراردادشده", s.contracted, "success"]].forEach(([label, value, tone]) => kpis.append(DashboardKpiCard({ label, value, tone })));
      const filtersArea = node("div"); const pilotsArea = node("div");
      const dashboardFilters = DashboardFilters({ values: filters, onChange: (values) => { filters = { ...filters, ...values, page: 1 }; writeFilters(filters); renderPilots(pilotsArea); } }); filtersArea.append(dashboardFilters);
      const operational = node("div", "dashboard-operational"); const actionsPanel = MyActions({ response: actions }); actionsPanel.id = "dashboard-actions"; operational.append(actionsPanel, widgetFor("sla", sla), widgetFor("incidents", incidents));
      const widgets = node("div", "dashboard-widgets"); [["stages", stages], ["gates", gates], ["missions", missions], ["forms", forms], ["commercial", commercial]].forEach(([kind, response]) => widgets.append(widgetFor(kind, response))); widgets.append(RecentActivities({ response: activities }));
      content.append(kpis, filtersArea, pilotsArea, operational, widgets);
      if (has(permissions, "notifications.read")) {
        const notifications = node("section", "dashboard-panel dashboard-widget"); notifications.append(node("h2", "dashboard-panel__title", "اعلان‌های اخیر"));
        notificationService.getNotifications({ page: 1, page_size: 5 }).then((response) => notifications.append(SummaryWidget({ title: "", items: response.items ?? [], keyName: "title", valueName: "priority" }).querySelector(".dashboard-widget__list") ?? node("p", "dashboard-state", "اعلانی وجود ندارد."))).catch(() => notifications.append(node("p", "dashboard-state", "دریافت اعلان‌ها انجام نشد."))); widgets.append(notifications);
      }
      const powerBI = PowerBIReport({ service: dashboardService, enabled: has(permissions, "reports.powerbi") }); powerBI.id = "powerbi-report"; content.append(powerBI);
      renderPilots(pilotsArea);
    } catch (error) {
      const state = node("section", "dashboard-panel dashboard-state dashboard-state--error", error.status === 403 ? "به نمای کلی دسترسی ندارید." : "دریافت اطلاعات داشبورد انجام نشد."); const retry = node("button", "button button--primary", "تلاش مجدد"); retry.type = "button"; retry.onclick = load; state.append(retry); content.replaceChildren(state);
    }
  };
  load(); return page;
};
