import { formatPersianDate } from "../utils/dateFormatter.js";

const STATUS_LABELS = Object.freeze({
  candidate: "نامزد پایلوت",
  awaiting_documents: "در انتظار مدارک",
  ready_for_capture: "آماده برداشت",
  operations: "عملیات",
  tour_building: "در حال ساخت تور",
  ready_to_view: "آماده مشاهده",
  evaluation: "در ارزیابی",
  proposal_sent: "پیشنهاد ارسال‌شده",
  converted: "تبدیل‌شده",
  closed: "بسته‌شده",
});

const SLA_LABELS = Object.freeze({
  on_track: "در محدوده SLA",
  at_risk: "نزدیک به سررسید",
  overdue: "SLA گذشته",
});

const createElement = (tagName, className, textContent = "") => {
  const element = document.createElement(tagName);

  element.className = className;
  element.textContent = textContent;

  return element;
};

const createMetadata = (label, value) => {
  const item = createElement("div", "pilot-card__metadata-item");
  const term = createElement("dt", "pilot-card__metadata-label", label);
  const description = createElement("dd", "pilot-card__metadata-value", value);

  item.append(term, description);

  return item;
};

export const PilotCard = ({ pilot }) => {
  const item = document.createElement("li");
  const header = createElement("header", "pilot-card__header");
  const identity = createElement("div", "pilot-card__identity");
  const code = createElement("span", "pilot-card__code", pilot.pilotCode);
  const title = createElement("h2", "pilot-card__title", pilot.displayName);
  const status = createElement(
    "span",
    "status-badge",
    STATUS_LABELS[pilot.status] ?? "نامشخص",
  );
  const progress = createElement("div", "pilot-card__progress");
  const progressText = createElement(
    "span",
    "pilot-card__progress-label",
    `مرحله ${pilot.currentStage} از ۱۹`,
  );
  const progressBar = document.createElement("progress");
  const metadata = document.createElement("dl");
  const sla = createElement(
    "span",
    `sla-badge sla-badge--${pilot.slaStatus}`,
    SLA_LABELS[pilot.slaStatus] ?? "وضعیت نامشخص",
  );
  const detailsLink = createElement(
    "a",
    "button button--ghost pilot-card__details-link",
    "مشاهده جزئیات",
  );

  item.className = "pilot-card";
  progressBar.className = "pilot-card__progress-bar";
  progressBar.max = 19;
  progressBar.value = pilot.currentStage;
  progressBar.setAttribute("aria-label", progressText.textContent);
  metadata.className = "pilot-card__metadata";
  detailsLink.href = `#/pilots/${pilot.id}`;

  identity.append(code, title);
  header.append(identity, status);
  progress.append(progressText, progressBar);
  metadata.append(
    createMetadata("مسئول فعلی", pilot.assigneeName),
    createMetadata("موعد", formatPersianDate(pilot.dueAt)),
  );
  item.append(header, progress, metadata, sla, detailsLink);

  return item;
};
