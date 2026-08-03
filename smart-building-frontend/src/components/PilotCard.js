import { formatPersianDate } from "../utils/dateFormatter.js";
import { translateDisplayValue } from "../utils/displayText.js";

const STATUS_LABELS = Object.freeze({
  candidate: "نامزد پایلوت",
  active: "فعال",
  converted: "تبدیل‌شده",
  closed: "بسته‌شده",
});

const element = (tag, className, text = "") => {
  const node = document.createElement(tag);
  node.className = className;
  node.textContent = text;
  return node;
};

const metadata = (label, value) => {
  const item = element("div", "pilot-card__metadata-item");
  item.append(
    element("dt", "pilot-card__metadata-label", label),
    element("dd", "pilot-card__metadata-value", value),
  );
  return item;
};

export const PilotCard = ({ pilot }) => {
  const item = element("li", "pilot-card");
  const header = element("header", "pilot-card__header");
  const identity = element("div", "pilot-card__identity");
  const progress = element("div", "pilot-card__progress");
  const progressText = element(
    "span",
    "pilot-card__progress-label",
    `مرحله ${pilot.currentStage} از ۱۹`,
  );
  const progressBar = document.createElement("progress");
  const details = element(
    "a",
    "button button--ghost pilot-card__details-link",
    "مشاهده جزئیات",
  );
  const info = document.createElement("dl");

  identity.append(
    element("span", "pilot-card__code", pilot.code),
    element("h2", "pilot-card__title", pilot.displayName),
  );
  header.append(
    identity,
    element(
      "span",
      "status-badge",
      STATUS_LABELS[pilot.status] ?? translateDisplayValue(pilot.status, "وضعیت نامشخص"),
    ),
  );
  progressBar.className = "pilot-card__progress-bar";
  progressBar.max = 19;
  progressBar.value = pilot.currentStage;
  progressBar.setAttribute("aria-label", progressText.textContent);
  progress.append(progressText, progressBar);
  info.className = "pilot-card__metadata";
  info.append(
    metadata("نام سیستمی", pilot.projectSystemName),
    metadata("تاریخ ایجاد", formatPersianDate(pilot.createdAt)),
  );
  details.href = `#/pilots/${pilot.id}`;
  item.append(header, progress, info, details);
  return item;
};
