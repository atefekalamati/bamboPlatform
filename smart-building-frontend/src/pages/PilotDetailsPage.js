import { StageStepper } from "../components/StageStepper.js";
import { PilotFormsPanel } from "../components/PilotFormsPanel.js";
import { PilotIncidentsPanel } from "../components/PilotIncidentsPanel.js";
import { PhoneCallLink } from "../components/PhoneCallLink.js";
import { sessionStore } from "../app/sessionStore.js";
import { pilotService } from "../services/pilotService.js";
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

const summaryItem = (label, value) => {
  const item = element("div", "pilot-summary__item");
  const content = element("dd", "pilot-summary__value");
  if (value instanceof Node) content.append(value);
  else content.textContent = value;
  item.append(
    element("dt", "pilot-summary__label", label),
    content,
  );
  return item;
};

const renderDetails = (container, pilot) => {
  const back = element("a", "back-link", "بازگشت به فهرست پرونده‌ها");
  const heading = element("header", "pilot-details__heading");
  const identity = element("div", "pilot-details__identity");
  const summary = element("dl", "pilot-summary");
  const project = pilot.project;
  const owner = project.owner;

  back.href = "#/pilots";
  identity.append(
    element("span", "pilot-details__code", pilot.code),
    element("h1", "page-heading__title", pilot.displayName),
  );
  heading.append(
    identity,
    element(
      "span",
      "status-badge",
      STATUS_LABELS[pilot.status] ?? translateDisplayValue(pilot.status, "وضعیت نامشخص"),
    ),
  );
  summary.append(
    summaryItem("نام سیستمی", pilot.projectSystemName),
    summaryItem("نام پروژه", project.name),
    summaryItem("مالک", owner.name),
    summaryItem("تصمیم‌گیرنده", `${owner.decisionMakerName} — ${owner.decisionMakerPosition}`),
    summaryItem("موبایل مالک", PhoneCallLink({
      phoneNumber: owner.primaryMobile,
      label: owner.primaryMobile,
      ariaLabel: `تماس با مالک پروژه، ${owner.name}`,
    })),
    summaryItem("تعداد طبقات", String(project.totalFloors)),
    summaryItem("مرحله پروژه", project.progressStage),
    summaryItem("مرحله پایلوت", `${pilot.currentStage} از ۱۹`),
    summaryItem("تاریخ ایجاد", formatPersianDate(pilot.createdAt)),
    summaryItem("آدرس", project.address),
    summaryItem("نیاز مشتری", project.customerNeed),
    summaryItem("ارزش مورد انتظار", project.expectedValue),
  );
  const sections = [
    back,
    heading,
    summary,
    StageStepper({
      stages: pilot.stages,
      currentStage: pilot.currentStage,
      pilotId: pilot.id,
    }),
    PilotFormsPanel({ pilotId: pilot.id }),
  ];
  if ((sessionStore.getCurrentUser()?.permissions ?? []).includes("incidents.read")) sections.push(PilotIncidentsPanel({ pilotId: pilot.id }));
  container.replaceChildren(...sections);
};

export const PilotDetailsPage = ({ pilotId }) => {
  const page = element("div", "pilot-details");
  const load = async () => {
    page.replaceChildren(
      element("p", "loading-state", "در حال دریافت جزئیات پرونده..."),
    );
    try {
      renderDetails(page, await pilotService.getPilotById(pilotId));
    } catch (error) {
      const state = element("div", "error-state");
      const retry = element("button", "button button--primary", "تلاش مجدد");
      const back = element("a", "button button--ghost", "بازگشت به فهرست");
      retry.type = "button";
      retry.addEventListener("click", load);
      back.href = "#/pilots";
      state.append(
        element(
          "p",
          "error-state__message",
          error.message ?? "دریافت جزئیات پرونده انجام نشد.",
        ),
        retry,
        back,
      );
      page.replaceChildren(state);
    }
  };
  page.setAttribute("aria-live", "polite");
  load();
  return page;
};
