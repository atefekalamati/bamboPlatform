import {
  clearNavigationGuard,
  setNavigationGuard,
} from "../app/navigationGuard.js";
import { StageOneForm } from "../components/StageOneForm.js";
import { pilotService } from "../services/pilotService.js";
import { stageService } from "../services/stageService.js";
import { formatPersianDate } from "../utils/dateFormatter.js";

const createElement = (tagName, className, textContent = "") => {
  const element = document.createElement(tagName);

  element.className = className;
  element.textContent = textContent;

  return element;
};

const createHeader = (pilot) => {
  const header = createElement("header", "stage-workspace__header");
  const identity = createElement("div", "stage-workspace__identity");
  const eyebrow = createElement(
    "span",
    "page-heading__eyebrow",
    `${pilot.pilotCode} — مرحله ۱ از ۱۹`,
  );
  const title = createElement(
    "h1",
    "page-heading__title",
    "انتخاب پروژه مناسب برای پایلوت",
  );
  const description = createElement(
    "p",
    "page-heading__description",
    "اطلاعات اولیه و چک‌لیست تناسب پروژه را تکمیل و به‌صورت پیش‌نویس ذخیره کنید.",
  );
  const status = createElement(
    "span",
    "status-badge stage-workspace__status",
    "پیش‌نویس",
  );

  identity.append(eyebrow, title, description);
  header.append(identity, status);

  return { element: header, status };
};

const createActions = () => {
  const container = createElement("div", "stage-actions");
  const saveButton = createElement(
    "button",
    "button button--primary",
    "ذخیره پیش‌نویس",
  );
  const reviewButton = createElement(
    "button",
    "button button--ghost",
    "بررسی آمادگی مرحله",
  );
  const feedback = createElement("p", "stage-actions__feedback");

  saveButton.type = "button";
  reviewButton.type = "button";
  feedback.setAttribute("role", "status");
  feedback.setAttribute("aria-live", "polite");
  container.append(saveButton, reviewButton, feedback);

  return { element: container, saveButton, reviewButton, feedback };
};

const renderWorkspace = ({ container, pilot, draft }) => {
  const backLink = createElement("a", "back-link", "بازگشت به جزئیات پرونده");
  const header = createHeader(pilot);
  const draftInfo = createElement(
    "p",
    "draft-info",
    draft.savedAt
      ? `آخرین ذخیره: ${formatPersianDate(draft.savedAt)}`
      : "این مرحله هنوز ذخیره نشده است.",
  );
  const actions = createActions();
  let isDirty = false;

  backLink.href = `#/pilots/${pilot.id}`;

  const markAsDirty = () => {
    if (isDirty) return;

    isDirty = true;
    header.status.textContent = "تغییرات ذخیره‌نشده";
    setNavigationGuard(() =>
      window.confirm(
        "تغییرات این مرحله ذخیره نشده است. آیا می‌خواهید از صفحه خارج شوید؟",
      ),
    );
  };

  const stageForm = StageOneForm({
    initialData: draft,
    onChange: markAsDirty,
  });

  actions.saveButton.addEventListener("click", async () => {
    actions.saveButton.disabled = true;
    actions.feedback.textContent = "در حال ذخیره...";

    try {
      const response = await stageService.saveStageDraft(
        pilot.id,
        1,
        stageForm.getData(),
      );
      isDirty = false;
      clearNavigationGuard();
      header.status.textContent = "پیش‌نویس ذخیره‌شده";
      draftInfo.textContent = `آخرین ذخیره: ${formatPersianDate(
        response.data.savedAt,
      )}`;
      actions.feedback.textContent = response.message;
    } catch (error) {
      actions.feedback.textContent =
        error.message ?? "ذخیره پیش‌نویس انجام نشد.";
    } finally {
      actions.saveButton.disabled = false;
    }
  });

  actions.reviewButton.addEventListener("click", () => {
    const errors = stageForm.validate();

    if (errors.length) {
      header.status.textContent = "اطلاعات ناقص";
      actions.feedback.textContent = `${errors.length} مورد نیازمند اصلاح است.`;
      document.getElementById(errors[0].fieldId)?.focus();
      return;
    }

    header.status.textContent = "آماده بررسی";
    actions.feedback.textContent =
      "فرم از نظر اولیه کامل است. ارسال واقعی پس از اتصال Backend فعال می‌شود.";
  });

  container.replaceChildren(
    backLink,
    header.element,
    draftInfo,
    stageForm.element,
    actions.element,
  );
};

export const StageOnePage = ({ pilotId }) => {
  const page = createElement("div", "stage-workspace");
  const loading = createElement(
    "p",
    "loading-state",
    "در حال آماده‌سازی مرحله...",
  );

  const renderUnavailable = (message, canRetry = false) => {
    const state = createElement("div", "error-state");
    const text = createElement("p", "error-state__message", message);
    const actions = createElement("div", "error-state__actions");
    const backLink = createElement(
      "a",
      "button button--ghost",
      "بازگشت به جزئیات پرونده",
    );

    backLink.href = `#/pilots/${pilotId}`;
    actions.append(backLink);

    if (canRetry) {
      const retryButton = createElement(
        "button",
        "button button--primary",
        "تلاش مجدد",
      );
      retryButton.type = "button";
      retryButton.addEventListener("click", loadWorkspace);
      actions.prepend(retryButton);
    }

    state.append(text, actions);
    page.replaceChildren(state);
  };

  const loadWorkspace = async () => {
    page.setAttribute("aria-busy", "true");
    page.replaceChildren(loading);

    try {
      const [pilotResponse, draftResponse] = await Promise.all([
        pilotService.getPilotById(pilotId),
        stageService.getStageDraft(pilotId, 1),
      ]);

      if (pilotResponse.data.currentStage !== 1) {
        renderUnavailable(
          "مرحله ۱ برای این پرونده جاری نیست و فقط Snapshot آن باید مشاهده شود.",
        );
        return;
      }

      renderWorkspace({
        container: page,
        pilot: pilotResponse.data,
        draft: draftResponse.data,
      });
    } catch (error) {
      renderUnavailable(
        error.message ?? "فضای کاری مرحله آماده نشد.",
        true,
      );
    } finally {
      page.setAttribute("aria-busy", "false");
    }
  };

  loadWorkspace();

  return page;
};
