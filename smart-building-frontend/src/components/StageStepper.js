import { formatPersianDate } from "../utils/dateFormatter.js";

const STATUS_LABELS = Object.freeze({
  approved: "تأییدشده",
  in_progress: "در حال انجام",
  needs_revision: "نیازمند اصلاح",
  locked: "قفل‌شده",
});

const createElement = (tagName, className, textContent = "") => {
  const element = document.createElement(tagName);

  element.className = className;
  element.textContent = textContent;

  return element;
};

const createDetailRow = (label, value) => {
  const row = createElement("div", "stage-detail__row");
  const term = createElement("dt", "stage-detail__label", label);
  const description = createElement("dd", "stage-detail__value", value);

  row.append(term, description);

  return row;
};

const renderStageDetails = (container, stage) => {
  const heading = createElement(
    "h3",
    "stage-detail__title",
    `مرحله ${stage.number}: ${stage.name}`,
  );
  const status = createElement(
    "span",
    `stage-status stage-status--${stage.status}`,
    STATUS_LABELS[stage.status] ?? "نامشخص",
  );
  const metadata = createElement("dl", "stage-detail__metadata");

  metadata.append(
    createDetailRow("مسئول", stage.assigneeName),
    createDetailRow("موعد", formatPersianDate(stage.dueAt)),
    createDetailRow("Gate مرتبط", stage.gateName ?? "ندارد"),
    createDetailRow(
      "Snapshot",
      stage.hasSnapshot ? "نسخه تأییدشده موجود است" : "موجود نیست",
    ),
  );
  container.replaceChildren(heading, status, metadata);
};

export const StageStepper = ({ stages, currentStage, pilotId }) => {
  const wrapper = createElement("section", "stage-section");
  const heading = createElement("h2", "stage-section__title", "مراحل پایلوت");
  const description = createElement(
    "p",
    "stage-section__description",
    "برای مشاهده اطلاعات هر مرحله، آن را انتخاب کنید.",
  );
  const layout = createElement("div", "stage-section__layout");
  const list = createElement("ol", "stage-stepper");
  const details = createElement("article", "stage-detail");
  let selectedStageNumber = currentStage;

  list.setAttribute("aria-label", "۱۹ مرحله فرایند پایلوت");
  details.setAttribute("aria-live", "polite");

  const renderList = () => {
    list.replaceChildren();

    stages.forEach((stage) => {
      const item = createElement("li", "stage-stepper__item");
      const button = document.createElement("button");
      const number = createElement(
        "span",
        "stage-stepper__number",
        String(stage.number),
      );
      const content = createElement("span", "stage-stepper__content");
      const name = createElement("span", "stage-stepper__name", stage.name);
      const status = createElement(
        "span",
        "stage-stepper__status",
        STATUS_LABELS[stage.status] ?? "نامشخص",
      );

      button.className = `stage-stepper__button stage-stepper__button--${stage.status}`;
      button.type = "button";
      button.setAttribute(
        "aria-pressed",
        String(stage.number === selectedStageNumber),
      );
      content.append(name, status);
      button.append(number, content);
      button.addEventListener("click", () => {
        selectedStageNumber = stage.number;
        renderList();
        renderStageDetails(details, stage);

        if (stage.number === 1 && stage.status === "in_progress") {
          const workspaceLink = createElement(
            "a",
            "button button--primary stage-detail__action",
            "ورود به فضای کاری مرحله",
          );
          workspaceLink.href = `#/pilots/${pilotId}/stages/1`;
          details.append(workspaceLink);
        }
      });
      item.append(button);
      list.append(item);
    });
  };

  const selectedStage =
    stages.find((stage) => stage.number === currentStage) ?? stages[0];

  renderList();
  renderStageDetails(details, selectedStage);

  if (selectedStage.number === 1 && selectedStage.status === "in_progress") {
    const workspaceLink = createElement(
      "a",
      "button button--primary stage-detail__action",
      "ورود به فضای کاری مرحله",
    );
    workspaceLink.href = `#/pilots/${pilotId}/stages/1`;
    details.append(workspaceLink);
  }
  layout.append(list, details);
  wrapper.append(heading, description, layout);

  return wrapper;
};
