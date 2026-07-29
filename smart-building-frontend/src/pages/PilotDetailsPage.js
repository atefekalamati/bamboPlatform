import { StageStepper } from "../components/StageStepper.js";
import { pilotService } from "../services/pilotService.js";
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

const createElement = (tagName, className, textContent = "") => {
  const element = document.createElement(tagName);

  element.className = className;
  element.textContent = textContent;

  return element;
};

const createSummaryItem = (label, value) => {
  const item = createElement("div", "pilot-summary__item");
  const term = createElement("dt", "pilot-summary__label", label);
  const description = createElement("dd", "pilot-summary__value", value);

  item.append(term, description);

  return item;
};

const renderDetails = (container, pilot) => {
  const backLink = createElement(
    "a",
    "back-link",
    "بازگشت به فهرست پرونده‌ها",
  );
  const heading = createElement("header", "pilot-details__heading");
  const identity = createElement("div", "pilot-details__identity");
  const code = createElement("span", "pilot-details__code", pilot.pilotCode);
  const title = createElement("h1", "page-heading__title", pilot.displayName);
  const status = createElement(
    "span",
    "status-badge",
    STATUS_LABELS[pilot.status] ?? "نامشخص",
  );
  const summary = createElement("dl", "pilot-summary");

  backLink.href = "#/pilots";
  identity.append(code, title);
  heading.append(identity, status);
  summary.append(
    createSummaryItem("نام سیستمی پروژه", pilot.projectSystemName),
    createSummaryItem("مالک", pilot.ownerName),
    createSummaryItem("مسئول فعلی", pilot.assigneeName),
    createSummaryItem("مرحله جاری", `${pilot.currentStage} از ۱۹`),
    createSummaryItem("موعد مرحله", formatPersianDate(pilot.dueAt)),
  );
  container.replaceChildren(
    backLink,
    heading,
    summary,
    StageStepper({
      stages: pilot.stages,
      currentStage: pilot.currentStage,
      pilotId: pilot.id,
    }),
  );
};

export const PilotDetailsPage = ({ pilotId }) => {
  const page = createElement("div", "pilot-details");
  const loading = createElement(
    "p",
    "loading-state",
    "در حال دریافت جزئیات پرونده...",
  );

  const loadPilot = async () => {
    page.setAttribute("aria-busy", "true");
    page.replaceChildren(loading);

    try {
      const response = await pilotService.getPilotById(pilotId);
      renderDetails(page, response.data);
    } catch (error) {
      const state = createElement("div", "error-state");
      const message = createElement(
        "p",
        "error-state__message",
        error.message ?? "دریافت جزئیات پرونده انجام نشد.",
      );
      const actions = createElement("div", "error-state__actions");
      const retryButton = createElement(
        "button",
        "button button--primary",
        "تلاش مجدد",
      );
      const backLink = createElement(
        "a",
        "button button--ghost",
        "بازگشت به فهرست",
      );

      retryButton.type = "button";
      retryButton.addEventListener("click", loadPilot);
      backLink.href = "#/pilots";
      actions.append(retryButton, backLink);
      state.append(message, actions);
      page.replaceChildren(state);
    } finally {
      page.setAttribute("aria-busy", "false");
    }
  };

  page.setAttribute("aria-live", "polite");
  loadPilot();

  return page;
};
