import { formatPersianDate } from "../utils/dateFormatter.js";

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
    row("زمان ارسال", formatPersianDate(stage.submittedAt)),
    row("زمان تأیید", formatPersianDate(stage.approvedAt)),
    row(
      "Gate مرتبط",
      stage.gate
        ? `${stage.gate.code} — ${stage.gate.title} (${stage.gate.status})`
        : "ندارد",
    ),
  );
  container.replaceChildren(
    element(
      "h3",
      "stage-detail__title",
      `مرحله ${stage.number}: ${stage.title}`,
    ),
    element(
      "span",
      `stage-status stage-status--${stage.status}`,
      STATUS_LABELS[stage.status] ?? stage.status,
    ),
    metadata,
  );
  if (
    stage.number === 1 &&
    ["open", "submitted", "needs_revision", "approved"].includes(stage.status)
  ) {
    const action = element(
      "a",
      "button button--primary stage-detail__action",
      stage.status === "approved" ? "مشاهده مرحله ۱" : "ورود به مرحله ۱",
    );
    action.href = `#/pilots/${container.dataset.pilotId}/stages/1`;
    container.append(action);
  }
};

export const StageStepper = ({ stages, currentStage, pilotId }) => {
  const wrapper = element("section", "stage-section");
  const layout = element("div", "stage-section__layout");
  const list = element("ol", "stage-stepper");
  const details = element("article", "stage-detail");
  let selected = currentStage;

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
      content.append(
        element("span", "stage-stepper__name", stage.title),
        element(
          "span",
          "stage-stepper__status",
          STATUS_LABELS[stage.status] ?? stage.status,
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
  details.dataset.pilotId = pilotId;
  renderList();
  if (selectedStage) renderDetails(details, selectedStage);
  layout.append(list, details);
  wrapper.append(
    element("h2", "stage-section__title", "مراحل پایلوت"),
    element(
      "p",
      "stage-section__description",
      "وضعیت واقعی هر مرحله و Gate مرتبط را مشاهده کنید.",
    ),
    layout,
  );
  return wrapper;
};
