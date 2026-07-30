import { sessionStore } from "../app/sessionStore.js";
import {
  clearNavigationGuard,
  setNavigationGuard,
} from "../app/navigationGuard.js";
import {
  StageReviewPanel,
  StageSnapshots,
  stageElement as element,
} from "../components/StageShared.js";
import { dwgService } from "../services/dwgService.js";
import { missionService } from "../services/missionService.js";
import { pilotService } from "../services/pilotService.js";
import { stageService } from "../services/stageService.js";

const STATUS_LABELS = Object.freeze({
  open: "باز",
  submitted: "در انتظار بررسی",
  approved: "تأییدشده",
  needs_revision: "نیازمند اصلاح",
  locked: "قفل‌شده",
});

const CAPTURE_STATES = Object.freeze([
  ["not_started", "شروع نشده"],
  ["incomplete", "ناقص"],
  ["not_done", "انجام نشده"],
  ["needs_revision", "نیازمند اصلاح"],
  ["completed", "تکمیل‌شده"],
]);

const CAPTURE_ITEMS = Object.freeze([
  ["correctFloor", "طبقه صحیح با مأموریت تطبیق داده شد."],
  ["startPointConfirmed", "نقطه شروع برداشت تأیید شد."],
  ["mainCaptureStarted", "برداشت اصلی آغاز شد."],
  ["continuousRoute", "مسیر برداشت پیوسته و بدون گسست بود."],
  ["coverageCompleted", "پوشش کامل محدوده طبقه انجام شد."],
  ["captureFinished", "برداشت طبقه به پایان رسید."],
  ["savedInMainApp", "نتیجه در اپلیکیشن اصلی ذخیره شد."],
]);

const localDateTime = (value) => (value ? value.slice(0, 16) : "");

const floorCaptureForm = ({ floor, state, disabled, onChange }) => {
  const section = element("section", "floor-workspace");
  const header = element("div", "floor-workspace__header");
  const form = document.createElement("form");
  const stateField = element("div", "stage-form__field");
  const stateLabel = element("label", "stage-form__label", "وضعیت برداشت");
  const captureState = document.createElement("select");
  const timing = element("div", "stage-form__grid");
  const startField = element("div", "stage-form__field");
  const startLabel = element("label", "stage-form__label", "زمان شروع برداشت");
  const startedAt = document.createElement("input");
  const finishField = element("div", "stage-form__field");
  const finishLabel = element("label", "stage-form__label", "زمان پایان برداشت");
  const finishedAt = document.createElement("input");
  const checklist = document.createElement("fieldset");
  const checklistItems = new Map();
  const failureField = element("div", "stage-form__field");
  const failureLabel = element(
    "label",
    "stage-form__label",
    "دلیل ناقص‌ماندن یا نیاز به اصلاح",
  );
  const failureReason = document.createElement("textarea");

  header.append(
    element("h2", "stage-form__legend", `${floor.code} — ${floor.name}`),
    element(
      "span",
      "status-badge",
      CAPTURE_STATES.find(([value]) => value === state.capture_state)?.[1] ??
        state.capture_state,
    ),
  );
  form.className = "stage-form";
  stateLabel.htmlFor = `stage7-state-${floor.id}`;
  captureState.id = `stage7-state-${floor.id}`;
  captureState.className = "stage-form__control";
  captureState.disabled = disabled;
  CAPTURE_STATES.forEach(([value, label]) =>
    captureState.append(new Option(label, value)),
  );
  captureState.value = state.capture_state;
  stateField.append(stateLabel, captureState);

  startLabel.htmlFor = `stage7-start-${floor.id}`;
  startedAt.id = `stage7-start-${floor.id}`;
  startedAt.type = "datetime-local";
  startedAt.className = "stage-form__control";
  startedAt.value = localDateTime(state.capture_started_at);
  startedAt.disabled = disabled;
  startField.append(startLabel, startedAt);
  finishLabel.htmlFor = `stage7-finish-${floor.id}`;
  finishedAt.id = `stage7-finish-${floor.id}`;
  finishedAt.type = "datetime-local";
  finishedAt.className = "stage-form__control";
  finishedAt.value = localDateTime(state.capture_finished_at);
  finishedAt.disabled = disabled;
  finishField.append(finishLabel, finishedAt);
  timing.append(startField, finishField);

  checklist.className = "checklist";
  checklist.append(
    element("legend", "checklist__legend", "کنترل‌های برداشت طبقه"),
  );
  const initialValues = {
    correctFloor: state.correct_floor,
    startPointConfirmed: state.start_point_confirmed,
    mainCaptureStarted: state.main_capture_started,
    continuousRoute: state.continuous_route,
    coverageCompleted: state.coverage_completed,
    captureFinished: state.capture_finished,
    savedInMainApp: state.saved_in_main_app,
  };
  CAPTURE_ITEMS.forEach(([key, label]) => {
    const item = element("label", "checklist__item");
    const checkbox = document.createElement("input");
    checkbox.type = "checkbox";
    checkbox.checked = Boolean(initialValues[key]);
    checkbox.disabled = disabled;
    checkbox.addEventListener("change", () => {
      item.classList.remove("checklist__item--invalid");
      onChange();
    });
    item.append(checkbox, element("span", "", label));
    checklist.append(item);
    checklistItems.set(key, { checkbox, item });
  });

  failureLabel.htmlFor = `stage7-failure-${floor.id}`;
  failureReason.id = `stage7-failure-${floor.id}`;
  failureReason.className = "stage-form__control";
  failureReason.value = state.failure_reason ?? "";
  failureReason.disabled = disabled;
  failureField.append(
    failureLabel,
    failureReason,
    element(
      "p",
      "draft-info",
      "برای وضعیت‌های ناقص، انجام‌نشده یا نیازمند اصلاح، ثبت دلیل الزامی است.",
    ),
  );
  [captureState, startedAt, finishedAt, failureReason].forEach((control) =>
    control.addEventListener("input", () => {
      control.removeAttribute("aria-invalid");
      onChange();
    }),
  );
  form.append(stateField, timing, checklist, failureField);
  section.append(header, form);

  const getData = () => ({
    captureState: captureState.value,
    ...Object.fromEntries(
      [...checklistItems].map(([key, { checkbox }]) => [
        key,
        checkbox.checked,
      ]),
    ),
    captureStartedAt: startedAt.value,
    captureFinishedAt: finishedAt.value,
    failureReason: failureReason.value.trim(),
    mainUploadStarted: state.main_upload_started,
    mainUploadCompleted: state.main_upload_completed,
    correctFloorLink: state.correct_floor_link,
    operationsNotified: state.operations_notified,
  });

  const validateForSave = () => {
    const values = getData();
    const unresolved = !["not_started", "completed"].includes(
      values.captureState,
    );
    const failureInvalid = unresolved && !values.failureReason;
    failureReason.setAttribute("aria-invalid", String(failureInvalid));
    const completed = values.captureState === "completed";
    let checklistValid = true;
    checklistItems.forEach(({ checkbox, item }) => {
      const invalid = completed && !checkbox.checked;
      item.classList.toggle("checklist__item--invalid", invalid);
      checklistValid = checklistValid && !invalid;
    });
    const missingCompletedTime =
      completed &&
      (!values.captureStartedAt || !values.captureFinishedAt);
    const invalidTimeOrder =
      values.captureStartedAt &&
      values.captureFinishedAt &&
      new Date(values.captureFinishedAt) < new Date(values.captureStartedAt);
    const dateInvalid = missingCompletedTime || invalidTimeOrder;
    startedAt.setAttribute("aria-invalid", String(dateInvalid));
    finishedAt.setAttribute("aria-invalid", String(dateInvalid));
    return !failureInvalid && !dateInvalid && checklistValid;
  };

  const validateForSubmit = () => {
    const values = getData();
    let valid = values.captureState === "completed";
    captureState.setAttribute(
      "aria-invalid",
      String(values.captureState !== "completed"),
    );
    checklistItems.forEach(({ checkbox, item }) => {
      item.classList.toggle("checklist__item--invalid", !checkbox.checked);
      valid = valid && checkbox.checked;
    });
    const timesValid =
      values.captureStartedAt &&
      values.captureFinishedAt &&
      new Date(values.captureFinishedAt) >=
        new Date(values.captureStartedAt);
    startedAt.setAttribute("aria-invalid", String(!timesValid));
    finishedAt.setAttribute("aria-invalid", String(!timesValid));
    return Boolean(valid && timesValid);
  };

  return { element: section, getData, validateForSave, validateForSubmit };
};

export const StageSevenPage = ({ pilotId }) => {
  const page = element("div", "stage-workspace");
  const permissions = sessionStore.getCurrentUser()?.permissions ?? [];
  const canEdit = permissions.includes("missions.manage");
  const canSubmit = permissions.includes("checklists.manage");
  const canApprove = permissions.includes("gate_approval.approve");
  const canReject = permissions.includes("gate_approval.reject");

  const renderError = (message) => {
    const state = element("div", "error-state");
    const retry = element("button", "button button--primary", "تلاش مجدد");
    const back = element("a", "button button--ghost", "بازگشت به جزئیات");
    retry.type = "button";
    retry.addEventListener("click", () => load());
    back.href = `#/pilots/${pilotId}`;
    state.append(element("p", "error-state__message", message), retry, back);
    page.replaceChildren(state);
  };

  const load = async (notice = "") => {
    clearNavigationGuard();
    page.replaceChildren(
      element("p", "loading-state", "در حال دریافت عملیات برداشت Stage 7..."),
    );
    try {
      const [pilot, missions, floors, snapshots] = await Promise.all([
        pilotService.getPilotById(pilotId),
        missionService.getMissions(pilotId),
        dwgService.getFloors(pilotId),
        stageService.getSnapshots(pilotId, 7),
      ]);
      const stage = pilot.stages.find(({ number }) => number === 7);
      if (stage.status === "locked") {
        renderError("Stage 7 تا زمان تأیید Stage 6 قفل است.");
        return;
      }
      const mission = missions.at(-1);
      if (!mission) {
        renderError("مأموریت فعال برای ثبت برداشت پیدا نشد.");
        return;
      }
      const editable =
        canEdit && ["open", "needs_revision"].includes(stage.status);
      const feedback = element("p", "stage-actions__feedback", notice);
      const back = element("a", "back-link", "بازگشت به جزئیات پرونده");
      const header = element("header", "stage-workspace__header");
      const identity = element("div", "stage-workspace__identity");
      const forms = mission.floorStates.map((state) => {
        const floor = floors.find(({ id }) => id === state.floor_id);
        return floor
          ? floorCaptureForm({
              floor,
              state,
              disabled: !editable,
              onChange: () =>
                setNavigationGuard(() =>
                  window.confirm(
                    "تغییرات برداشت ذخیره نشده‌اند. از صفحه خارج می‌شوید؟",
                  ),
                ),
            })
          : null;
      }).filter(Boolean);
      back.href = `#/pilots/${pilot.id}`;
      identity.append(
        element(
          "span",
          "page-heading__eyebrow",
          `${pilot.code} — ${mission.code} — Stage 7 از ۱۹`,
        ),
        element("h1", "page-heading__title", "اجرای برداشت طبقات"),
        element(
          "p",
          "draft-info",
          "وضعیت، زمان و کنترل‌های برداشت باید برای تمام طبقات مأموریت ثبت شوند.",
        ),
      );
      header.append(
        identity,
        element(
          "span",
          "status-badge stage-workspace__status",
          STATUS_LABELS[stage.status] ?? stage.status,
        ),
      );
      page.replaceChildren(
        back,
        header,
        feedback,
        ...forms.map(({ element: formElement }) => formElement),
      );

      if (editable) {
        const actions = element("div", "stage-actions");
        const save = element(
          "button",
          "button button--ghost",
          "ذخیره عملیات طبقات",
        );
        const submit = element(
          "button",
          "button button--primary",
          "ارسال Stage 7 برای بررسی",
        );
        save.type = submit.type = "button";
        submit.hidden = !canSubmit;
        const saveAll = async () => {
          const validationResults = forms.map((form) =>
            form.validateForSave(),
          );
          if (!validationResults.every(Boolean)) {
            throw new Error(
              "دلیل وضعیت‌های ناقص و ترتیب زمان‌های قرمزشده را اصلاح کنید.",
            );
          }
          save.disabled = true;
          for (const [index, form] of forms.entries()) {
            await missionService.saveFloorCapture(
              mission.id,
              mission.floorStates[index].floor_id,
              form.getData(),
            );
          }
          clearNavigationGuard();
          feedback.textContent = "عملیات برداشت تمام طبقات ذخیره شد.";
          save.disabled = false;
        };
        save.addEventListener("click", async () => {
          try {
            await saveAll();
          } catch (error) {
            feedback.textContent = error.message;
            save.disabled = false;
          }
        });
        submit.addEventListener("click", async () => {
          const validationResults = forms.map((form) =>
            form.validateForSubmit(),
          );
          if (!validationResults.every(Boolean)) {
            feedback.textContent =
              "برای ارسال، تمام طبقات باید تکمیل و همه موارد قرمزشده اصلاح شوند.";
            return;
          }
          submit.disabled = true;
          try {
            await saveAll();
            await stageService.submit(pilot.id, 7);
            await load("Stage 7 برای بررسی ارسال شد.");
          } catch (error) {
            feedback.textContent = error.message;
            submit.disabled = false;
          }
        });
        actions.append(save, submit);
        page.append(actions);
      }

      if (stage.status === "submitted" && (canApprove || canReject)) {
        page.append(
          StageReviewPanel({
            pilotId: pilot.id,
            stageNumber: 7,
            title: "بررسی اجرای برداشت",
            approveLabel: "تأیید و ورود به Stage 8",
            approvedNotice: "Stage 7 تأیید شد و Stage 8 باز شد.",
            rejectedNotice: "Stage 7 برای اصلاح برگشت داده شد.",
            canApprove,
            canReject,
            reload: load,
          }),
        );
      }
      page.append(
        StageSnapshots({
          snapshots,
          title: "نسخه‌های تأییدشده Stage 7",
        }),
      );
    } catch (error) {
      renderError(error.message ?? "دریافت Stage 7 انجام نشد.");
    }
  };
  load();
  return page;
};
