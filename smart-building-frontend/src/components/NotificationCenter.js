import { notificationStore } from "../app/notificationStore.js";
import { sessionStore } from "../app/sessionStore.js";
import { translateActionTitle, translateDisplayValue } from "../utils/displayText.js";

const CATEGORY_LABELS = Object.freeze({
  AUTH: "احراز هویت", PILOT: "پایلوت", STAGE: "مرحله", MISSION: "مأموریت",
  INCIDENT: "رخداد", SLA: "زمان‌بندی", COMMERCIAL: "تجاری", SYSTEM: "سامانه",
});
const PRIORITY_LABELS = Object.freeze({ LOW: "کم", NORMAL: "عادی", HIGH: "مهم", CRITICAL: "بحرانی" });

const node = (tag, className = "", text = "") => {
  const item = document.createElement(tag);
  item.className = className;
  item.textContent = text;
  return item;
};

export const notificationLabels = Object.freeze({ categories: CATEGORY_LABELS, priorities: PRIORITY_LABELS });

export const relativeNotificationTime = (value) => {
  const timestamp = new Date(value).getTime();
  if (!Number.isFinite(timestamp)) return "زمان نامشخص";
  const minutes = Math.round((timestamp - Date.now()) / 60000);
  const formatter = new Intl.RelativeTimeFormat("fa", { numeric: "auto" });
  if (Math.abs(minutes) < 60) return formatter.format(minutes, "minute");
  const hours = Math.round(minutes / 60);
  if (Math.abs(hours) < 24) return formatter.format(hours, "hour");
  return formatter.format(Math.round(hours / 24), "day");
};

export const safeNotificationRoute = (actionUrl) => {
  if (typeof actionUrl !== "string") return null;
  const clean = actionUrl.trim();
  if (!/^\/(pilots(?:\/[^?#]*)?|notifications|settings\/notifications)(?:[?#].*)?$/.test(clean)) return null;
  return `#${clean}`;
};

export const createNotificationItem = ({ item, compact = false, onOpen, onMarkRead = null }) => {
  const article = node("article", `notification-item priority-${item.priority.toLowerCase()}${item.is_read ? " is-read" : " is-unread"}`);
  const icon = node("span", "notification-item__icon", item.priority === "CRITICAL" ? "!" : "●");
  icon.setAttribute("aria-hidden", "true");
  const content = node("div", "notification-item__content");
  const header = node("div", "notification-item__header");
  const visibleTitle = translateActionTitle(item.title, "اعلان سیستمی");
  const title = node("h3", "notification-item__title", visibleTitle);
  const time = node("time", "notification-item__time", relativeNotificationTime(item.created_at));
  time.dateTime = item.created_at;
  const rawBody = compact ? (item.short_body || item.body) : item.body;
  const body = node("p", "notification-item__body", translateDisplayValue(rawBody, "جزئیات این اعلان در سوابق عملیاتی ثبت شده است."));
  const meta = node("div", "notification-item__meta");
  meta.append(
    node("span", "notification-chip", CATEGORY_LABELS[item.category] ?? translateDisplayValue(item.category, "عمومی")),
    node("span", `notification-chip priority-${item.priority.toLowerCase()}`, `اولویت ${PRIORITY_LABELS[item.priority] ?? translateDisplayValue(item.priority, "عادی")}`),
  );
  if (!item.is_read) meta.append(node("span", "notification-item__unread", "خوانده‌نشده"));
  header.append(title, time);
  content.append(header, body, meta);
  article.append(icon, content);
  const open = () => onOpen(item);
  const interactiveTarget = onMarkRead ? content : article;
  interactiveTarget.tabIndex = 0;
  interactiveTarget.setAttribute("role", "button");
  interactiveTarget.setAttribute("aria-label", `${visibleTitle}، ${item.is_read ? "خوانده‌شده" : "خوانده‌نشده"}`);
  interactiveTarget.addEventListener("click", open);
  interactiveTarget.addEventListener("keydown", (event) => {
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      open();
    }
  });
  if (onMarkRead && !item.is_read) {
    article.classList.add("notification-item--with-action");
    const readButton = node("button", "button button--ghost notification-item__read", "خوانده شد");
    readButton.type = "button";
    readButton.setAttribute("aria-label", `علامت‌گذاری «${visibleTitle}» به‌عنوان خوانده‌شده`);
    readButton.addEventListener("click", async () => {
      readButton.disabled = true;
      readButton.textContent = "در حال ثبت…";
      try { await onMarkRead(item); }
      catch { readButton.disabled = false; readButton.textContent = "خوانده شد"; }
    });
    article.append(readButton);
  }
  return article;
};

const createBellIcon = () => {
  const holder = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  holder.setAttribute("viewBox", "0 0 24 24");
  holder.setAttribute("aria-hidden", "true");
  ["M18 8a6 6 0 0 0-12 0c0 7-3 7-3 9h18c0-2-3-2-3-9", "M10 21h4"].forEach((data) => {
    const path = document.createElementNS("http://www.w3.org/2000/svg", "path");
    path.setAttribute("d", data);
    holder.append(path);
  });
  return holder;
};

export const NotificationCenter = () => {
  const canMarkRead = (sessionStore.getCurrentUser()?.permissions ?? []).includes("notifications.mark_read");
  const root = node("div", "notification-center");
  const bell = node("button", "notification-bell");
  const badge = node("span", "notification-bell__badge");
  const dropdown = node("section", "notification-dropdown");
  bell.type = "button";
  bell.setAttribute("aria-label", "اعلان‌ها؛ در حال دریافت تعداد خوانده‌نشده");
  bell.setAttribute("aria-haspopup", "dialog");
  bell.setAttribute("aria-expanded", "false");
  bell.append(createBellIcon(), badge);
  dropdown.hidden = true;
  dropdown.setAttribute("aria-label", "اعلان‌های اخیر");

  const openItem = async (item) => {
    if (canMarkRead) await notificationStore.markAsRead(item.id).catch(() => null);
    dropdown.hidden = true;
    bell.setAttribute("aria-expanded", "false");
    window.location.hash = safeNotificationRoute(item.action_url) ?? `#/notifications/${encodeURIComponent(item.id)}`;
  };

  const render = (state) => {
    badge.hidden = state.unreadCount <= 0;
    badge.textContent = state.unreadCount > 99 ? "۹۹+" : String(state.unreadCount);
    bell.setAttribute("aria-label", `اعلان‌ها؛ ${state.unreadCount} اعلان خوانده‌نشده`);
    const header = node("header", "notification-dropdown__header");
    header.append(node("strong", "", "اعلان‌های اخیر"));
    if (state.unreadCount && canMarkRead) {
      const readAll = node("button", "button-link", "خواندن همه");
      readAll.type = "button";
      readAll.addEventListener("click", () => notificationStore.markAllAsRead().catch(() => null));
      header.append(readAll);
    }
    const list = node("div", "notification-dropdown__list");
    if (state.connectionStatus === "syncing" && !state.items.length) list.append(node("p", "notification-skeleton", "در حال دریافت اعلان‌ها…"));
    else if (state.error && !state.items.length) {
      const retry = node("button", "button button--ghost", "تلاش مجدد");
      retry.type = "button";
      retry.addEventListener("click", () => notificationStore.sync().catch(() => null));
      list.append(node("p", "error-state__message", "دریافت اعلان‌ها انجام نشد."), retry);
    } else if (!state.items.length) list.append(node("p", "notification-empty", "اعلان جدیدی ندارید."));
    else state.items.slice(0, 7).forEach((item) => list.append(createNotificationItem({ item, compact: true, onOpen: openItem })));
    const all = node("a", "notification-dropdown__all", "مشاهده همه اعلان‌ها");
    all.href = "#/notifications";
    all.addEventListener("click", () => { dropdown.hidden = true; });
    dropdown.replaceChildren(header, list, all);
  };

  const unsubscribe = notificationStore.subscribe(render);
  void unsubscribe;
  bell.addEventListener("click", () => {
    dropdown.hidden = !dropdown.hidden;
    bell.setAttribute("aria-expanded", String(!dropdown.hidden));
    if (!dropdown.hidden) dropdown.querySelector("[tabindex],button,a")?.focus();
  });
  document.addEventListener("click", (event) => {
    if (!root.contains(event.target)) {
      dropdown.hidden = true;
      bell.setAttribute("aria-expanded", "false");
    }
  });
  root.addEventListener("keydown", (event) => {
    if (event.key === "Escape") {
      dropdown.hidden = true;
      bell.setAttribute("aria-expanded", "false");
      bell.focus();
    }
  });
  root.append(bell, dropdown);
  notificationStore.start();
  return root;
};
