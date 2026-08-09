import { formatPersianDateTime } from "../utils/dateFormatter.js";
import { translateDisplayValue } from "../utils/displayText.js";

const STATUS_LABELS = Object.freeze({
  open: "باز",
  submitted: "ارسال‌شده",
  approved: "تأییدشده",
  needs_revision: "نیازمند اصلاح",
  locked: "قفل‌شده",
});

const element = (tag, className, text = "") => {
  const node = document.createElement(tag);
  node.className = className;
  node.textContent = text;
  return node;
};

const row = (label, value) => {
  const item = element("div", "stage-detail__row");
  item.append(
    element("dt", "stage-detail__label", label),
    element("dd", "stage-detail__value", value),
  );
  return item;
};

const renderDetails = (container, stage) => {
  const metadata = element("dl", "stage-detail__metadata");
  metadata.append(
    row("آخرین نسخه", String(stage.latestVersion)),
    row("زمان ارسال", formatPersianDateTime(stage.submittedAt)),
    row("زمان تأیید", formatPersianDateTime(stage.approvedAt)),
    row(
      "Gate مرتبط",
      stage.gate
        ? `${translateDisplayValue(stage.gate.code)} — ${stage.gate.title} (${translateDisplayValue(stage.gate.status, "وضعیت نامشخص")})`
        : "ندارد",
    ),
  );
  container.replaceChildren(
    element(
      "h3",
      "stage-detail__title",
      `${stage.number}. ${stage.title}`,
    ),
    element(
      "span",
      `stage-status stage-status--${stage.status}`,
      STATUS_LABELS[stage.status] ?? translateDisplayValue(stage.status, "وضعیت نامشخص"),
    ),
    metadata,
  );
  if (
    [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19].includes(stage.number) &&
    ["open", "submitted", "needs_revision", "approved"].includes(stage.status)
  ) {
    const action = element(
      "a",
      "button button--primary stage-detail__action",
      stage.status === "approved"
        ? `مشاهده مرحله ${stage.number}`
        : `ورود به مرحله ${stage.number}`,
    );
    action.href = `#/pilots/${container.dataset.pilotId}/stages/${stage.number}`;
    container.append(action);
  }
};

export const StageStepper = ({ stages, currentStage, pilotId }) => {
  const wrapper = element("section", "stage-section");
  const layout = element("div", "stage-section__layout");
  const list = element("ol", "stage-stepper");
  const details = element("article", "stage-detail");
  const approvedCount = stages.filter(({ status }) => status === "approved").length;
  const progressValue = Math.round((approvedCount / 19) * 100);
  const progressSummary = element("div", "stage-section__progress");
  const progress = document.createElement("progress");
  let selected = currentStage;

  progress.max = 100;
  progress.value = progressValue;
  progress.setAttribute("aria-label", `پیشرفت پرونده: ${progressValue} درصد`);
  progressSummary.append(
    element("strong", "stage-section__progress-value", `${progressValue}٪ تکمیل‌شده`),
    element("span", "stage-section__progress-count", `${approvedCount} مرحله از ۱۹ مرحله تأیید شده است`),
    progress,
  );

  const renderList = () => {
    list.replaceChildren();
    stages.forEach((stage) => {
      const item = element("li", "stage-stepper__item");
      const button = element(
        "button",
        `stage-stepper__button stage-stepper__button--${stage.status}`,
      );
      const content = element("span", "stage-stepper__content");
      button.type = "button";
      button.setAttribute("aria-pressed", String(stage.number === selected));
      button.setAttribute(
        "aria-label",
        `مرحله ${stage.number}: ${stage.title}، ${STATUS_LABELS[stage.status] ?? translateDisplayValue(stage.status, "وضعیت نامشخص")}`,
      );
      button.title = `${stage.title} — ${STATUS_LABELS[stage.status] ?? translateDisplayValue(stage.status, "وضعیت نامشخص")}`;
      content.append(
        element("span", "stage-stepper__name", stage.title),
        element(
          "span",
          "stage-stepper__status",
          STATUS_LABELS[stage.status] ?? translateDisplayValue(stage.status, "وضعیت نامشخص"),
        ),
      );
      button.append(
        element("span", "stage-stepper__number", String(stage.number)),
        content,
      );
      button.addEventListener("click", () => {
        selected = stage.number;
        renderList();
        renderDetails(details, stage);
      });
      item.append(button);
      list.append(item);
    });
  };

  const selectedStage =
    stages.find(({ number }) => number === currentStage) ?? stages[0];
  list.setAttribute("aria-label", "۱۹ مرحله فرایند پایلوت");
  details.setAttribute("aria-live", "polite");
  details.setAttribute("aria-label", "جزئیات مرحله انتخاب‌شده");
  details.dataset.pilotId = pilotId;
  renderList();
  if (selectedStage) renderDetails(details, selectedStage);
  layout.append(list, details);
  wrapper.append(
    element("h2", "stage-section__title", "وضعیت مراحل پروژه"),
    element("p", "stage-section__description", "برای مشاهده جزئیات، وضعیت و Gate مرتبط هر مرحله را انتخاب کنید."),
    progressSummary,
    layout,
  );
  return wrapper;
};
