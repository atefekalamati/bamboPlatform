import { notificationStore } from "../app/notificationStore.js";
import { sessionStore } from "../app/sessionStore.js";
import { createNotificationItem, notificationLabels, safeNotificationRoute } from "../components/NotificationCenter.js";
import { Pagination } from "../components/Pagination.js";
import { notificationService } from "../services/notificationService.js";
import { translateDisplayValue } from "../utils/displayText.js";

const node = (tag, className = "", text = "") => {
  const item = document.createElement(tag);
  item.className = className;
  item.textContent = text;
  return item;
};

const selectField = (labelText, options) => {
  const label = node("label", "notification-filter");
  const select = document.createElement("select");
  select.className = "form-field__input";
  options.forEach(([value, text]) => {
    const option = document.createElement("option");
    option.value = value;
    option.textContent = text;
    select.append(option);
  });
  label.append(node("span", "form-field__label", labelText), select);
  return { label, select };
};

export const NotificationsPage = ({ notificationId = null } = {}) => {
  const permissions = sessionStore.getCurrentUser()?.permissions ?? [];
  const page = node("div", "page notifications-page");
  if (!permissions.includes("notifications.read")) {
    page.append(node("p", "error-state__message", "برای مشاهده اعلان‌ها دسترسی ندارید."));
    return page;
  }
  const heading = node("header", "page-heading");
  heading.append(
    node("p", "page-heading__eyebrow", "ارتباطات درون‌برنامه‌ای"),
    node("h1", "page-heading__title", "مرکز اعلان‌ها"),
    node("p", "page-heading__description", "اعلان‌های مراحل، مأموریت‌ها، رخدادها و پیگیری‌های پروژه را اینجا مشاهده کنید."),
  );
  const tabs = node("div", "notification-tabs");
  tabs.setAttribute("role", "tablist");
  const toolbar = node("div", "notification-toolbar card");
  const category = selectField("دسته", [["", "همه دسته‌ها"], ...Object.entries(notificationLabels.categories).map(([value, label]) => [value, label])]);
  const priority = selectField("اولویت", [["", "همه اولویت‌ها"], ...Object.entries(notificationLabels.priorities).map(([value, label]) => [value, label])]);
  const refresh = node("button", "button button--ghost", "به‌روزرسانی");
  const readAll = node("button", "button button--primary", "خواندن همه");
  const settings = node("a", "button button--ghost", "تنظیمات اعلان‌ها");
  settings.href = "#/settings/notifications";
  refresh.type = readAll.type = "button";
  readAll.hidden = !permissions.includes("notifications.mark_read");
  toolbar.append(category.label, priority.label, refresh, readAll, settings);
  const summary = node("div", "notification-summary");
  const detail = node("section", "notification-detail card");
  detail.hidden = !notificationId;
  const content = node("section", "notification-list notification-glass-panel");
  const deliverySection = node("section", "notification-deliveries card");
  deliverySection.hidden = !permissions.includes("notifications.delivery_logs.read");
  if (!deliverySection.hidden) {
    const deliveryButton = node("button", "button button--ghost", "نمایش وضعیت ارسال پیامک‌ها");
    deliveryButton.type = "button";
    deliveryButton.addEventListener("click", async () => {
      deliveryButton.disabled = true;
      try {
        const labels = { PENDING: "در انتظار", QUEUED: "در صف ارسال", SENDING: "در حال ارسال", SENT: "ارسال شد", DELIVERED: "تحویل شد", FAILED: "ناموفق", CANCELLED: "لغو شد", SKIPPED: "طبق تنظیمات کاربر ارسال نشد" };
        const logs = await notificationService.getDeliveryLogs();
        const table = node("table", "notification-delivery-table");
        const head = document.createElement("thead");
        const headerRow = document.createElement("tr");
        ["کانال", "گیرنده", "وضعیت", "تعداد تلاش"].forEach((label) => {
          const header = document.createElement("th");
          header.scope = "col";
          header.textContent = label;
          headerRow.append(header);
        });
        head.append(headerRow);
        const body = document.createElement("tbody");
        logs.forEach((log) => { const row = document.createElement("tr"); [log.channel === "SMS" ? "پیامک" : "درون‌برنامه‌ای", log.recipient_address, labels[log.status] ?? translateDisplayValue(log.status, "وضعیت نامشخص"), String(log.attempt_count)].forEach((value) => row.append(node("td", "", value))); body.append(row); });
        table.append(head, body);
        deliverySection.replaceChildren(node("h2", "section-title", "وضعیت ارسال اعلان‌ها"), logs.length ? table : node("p", "notification-empty", "سابقه ارسالی وجود ندارد."));
      } catch (error) { deliveryButton.disabled = false; deliverySection.append(node("p", "error-state__message", error.message ?? "دریافت وضعیت ارسال انجام نشد.")); }
    });
    deliverySection.append(deliveryButton);
  }
  page.append(heading, tabs, toolbar, detail, summary, content, deliverySection);
  let activePage = 1;
  let statusFilter = "unread";

  const renderTabs = () => {
    tabs.replaceChildren();
    [["unread", "خوانده‌نشده"], ["read", "خوانده‌شده"], ["", "همه اعلان‌ها"]].forEach(([value, label]) => {
      const button = node("button", `notification-tabs__button${statusFilter === value ? " is-active" : ""}`, label);
      button.type = "button";
      button.setAttribute("role", "tab");
      button.setAttribute("aria-selected", String(statusFilter === value));
      button.addEventListener("click", () => {
        statusFilter = value;
        activePage = 1;
        readAll.hidden = !permissions.includes("notifications.mark_read") || statusFilter === "read";
        renderTabs();
        load();
      });
      tabs.append(button);
    });
  };

  const loadDetail = async () => {
    if (!notificationId) return;
    detail.hidden = false;
    detail.replaceChildren(node("p", "loading-state", "در حال دریافت جزئیات اعلان…"));
    try {
      const item = await notificationService.getNotification(notificationId);
      const close = node("a", "button button--ghost", "بستن جزئیات"); close.href = "#/notifications";
      detail.replaceChildren(createNotificationItem({ item, onOpen: async () => { if (permissions.includes("notifications.mark_read")) await notificationStore.markAsRead(item.id).catch(() => null); const route = safeNotificationRoute(item.action_url); if (route) window.location.hash = route; } }), close);
    } catch (error) { detail.replaceChildren(node("p", "error-state__message", error.message ?? "جزئیات اعلان دریافت نشد.")); }
  };

  const openItem = async (item) => {
    const route = safeNotificationRoute(item.action_url);
    window.location.hash = route ?? `#/notifications/${encodeURIComponent(item.id)}`;
  };

  const markItemRead = async (item) => {
    await notificationStore.markAsRead(item.id);
    await load();
  };

  const load = async () => {
    content.replaceChildren(node("p", "loading-state", "در حال دریافت اعلان‌ها…"));
    try {
      const response = await notificationService.getNotifications({
        page: activePage, page_size: 20, status: statusFilter,
        category: category.select.value, priority: priority.select.value,
      });
      summary.replaceChildren(
        node("strong", "", `${response.unread_count} اعلان خوانده‌نشده`),
        node("span", "muted-text", `از مجموع ${response.total} اعلان`),
      );
      const fragment = document.createDocumentFragment();
      if (!response.items.length) fragment.append(node("p", "notification-empty card", "اعلانی با این فیلتر پیدا نشد."));
      response.items.forEach((item) => fragment.append(createNotificationItem({
        item,
        onOpen: openItem,
        onMarkRead: permissions.includes("notifications.mark_read") ? markItemRead : null,
      })));
      if (response.total_pages > 1) fragment.append(Pagination({ activePage, totalPages: response.total_pages, onPageChange: (next) => { activePage = next; load(); } }));
      content.replaceChildren(fragment);
      notificationStore.sync().catch(() => null);
    } catch (error) {
      const retry = node("button", "button button--primary", "تلاش مجدد");
      retry.type = "button";
      retry.addEventListener("click", load);
      content.replaceChildren(node("p", "error-state__message", error.message ?? "دریافت اعلان‌ها انجام نشد."), retry);
    }
  };
  [category.select, priority.select].forEach((control) => control.addEventListener("change", () => { activePage = 1; load(); }));
  refresh.addEventListener("click", load);
  readAll.addEventListener("click", async () => { readAll.disabled = true; try { await notificationStore.markAllAsRead(); await load(); } finally { readAll.disabled = false; } });
  loadDetail();
  renderTabs();
  load();
  return page;
};
