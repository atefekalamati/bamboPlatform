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
  submitted: "در انتظار بررسی G3",
  approved: "تأییدشده",
  needs_revision: "نیازمند اصلاح",
  locked: "قفل‌شده",
});

const UPLOAD_ITEMS = Object.freeze([
  ["mainUploadStarted", "Upload در پلتفرم اصلی آغاز شده است."],
  ["mainUploadCompleted", "Upload در پلتفرم اصلی کامل شده است."],
  ["correctFloorLink", "فایل Uploadشده به طبقه صحیح متصل است."],
  ["operationsNotified", "تکمیل Upload به تیم عملیات اطلاع داده شده است."],
]);

// The API stores mission timestamps as UTC and currently serializes them
// without an explicit timezone. Preserve that meaning when Stage 9 sends the
// existing capture data back alongside the upload-only fields.
const backendUtcTime = (value) => {
  if (!value || /(?:Z|[+-]\d{2}:\d{2})$/.test(value)) return value;
  return `${value}Z`;
};

const floorValues = (state) => ({
  captureState: state.capture_state,
  correctFloor: state.correct_floor,
  startPointConfirmed: state.start_point_confirmed,
  mainCaptureStarted: state.main_capture_started,
  continuousRoute: state.continuous_route,
  coverageCompleted: state.coverage_completed,
  captureFinished: state.capture_finished,
  savedInMainApp: state.saved_in_main_app,
  captureStartedAt: backendUtcTime(state.capture_started_at),
  captureFinishedAt: backendUtcTime(state.capture_finished_at),
  mainUploadStarted: state.main_upload_started,
  mainUploadCompleted: state.main_upload_completed,
  correctFloorLink: state.correct_floor_link,
  operationsNotified: state.operations_notified,
  failureReason: state.failure_reason,
});

const uploadForm = ({ floor, state, disabled, onChange }) => {
  const section = element("section", "floor-workspace");
  const checklist = document.createElement("fieldset");
  const items = new Map();
  section.append(
    element("h2", "stage-form__legend", `${floor.code} — ${floor.name}`),
  );
  checklist.className = "checklist";
  checklist.append(
    element("legend", "checklist__legend", "وضعیت Upload طبقه"),
  );
  const initial = floorValues(state);
  UPLOAD_ITEMS.forEach(([key, label]) => {
    const item = element("label", "checklist__item");
    const checkbox = document.createElement("input");
    checkbox.type = "checkbox";
    checkbox.checked = Boolean(initial[key]);
    checkbox.disabled = disabled;
    checkbox.addEventListener("change", () => {
      item.classList.remove("checklist__item--invalid");
      onChange();
    });
    item.append(checkbox, element("span", "", label));
    checklist.append(item);
    items.set(key, { checkbox, item });
  });
  section.append(checklist);

  const getData = () => ({
    ...initial,
    ...Object.fromEntries(
      [...items].map(([key, { checkbox }]) => [key, checkbox.checked]),
    ),
  });
  const validateDependencies = () => {
    const values = getData();
    const invalid = {
      mainUploadStarted:
        values.mainUploadCompleted && !values.mainUploadStarted,
      mainUploadCompleted:
        (values.correctFloorLink || values.operationsNotified) &&
        !values.mainUploadCompleted,
      correctFloorLink:
        values.operationsNotified && !values.correctFloorLink,
      operationsNotified: false,
    };
    items.forEach(({ item }, key) =>
      item.classList.toggle("checklist__item--invalid", invalid[key]),
    );
    return !Object.values(invalid).some(Boolean);
  };
  const validateForSubmit = () => {
    let valid = true;
    items.forEach(({ checkbox, item }) => {
      item.classList.toggle("checklist__item--invalid", !checkbox.checked);
      valid = valid && checkbox.checked;
    });
    return valid;
  };
  return { element: section, getData, validateDependencies, validateForSubmit };
};

const normalizedTime = (value) =>
  value ? new Date(backendUtcTime(value)).toISOString() : null;

const missionTimes = (mission) => {
  const starts = mission.floorStates
    .map(({ capture_started_at: value }) => value)
    .filter(Boolean)
    .map((value) => new Date(backendUtcTime(value)));
  const finishes = mission.floorStates
    .map(({ capture_finished_at: value }) => value)
    .filter(Boolean)
    .map((value) => new Date(backendUtcTime(value)));
  return {
    startedAt:
      normalizedTime(mission.formF03.started_at) ??
      (starts.length
        ? new Date(Math.min(...starts.map(Number))).toISOString()
        : null),
    finishedAt:
      normalizedTime(mission.formF03.finished_at) ??
      (finishes.length
        ? new Date(Math.max(...finishes.map(Number))).toISOString()
        : null),
  };
};

const missionCompletion = ({ mission, disabled, onChange }) => {
  const section = document.createElement("fieldset");
  const completedItem = element("label", "checklist__item");
  const completed = document.createElement("input");
  const confirmedItem = element("label", "checklist__item");
  const confirmed = document.createElement("input");
  section.className = "checklist";
  section.append(
    element("legend", "checklist__legend", "تکمیل مأموریت و تأیید عملیات"),
  );
  completed.type = confirmed.type = "checkbox";
  completed.checked = Boolean(mission.formF03.mission_completed);
  confirmed.checked = Boolean(mission.formF03.operations_confirmed);
  completed.disabled = confirmed.disabled = disabled;
  completed.addEventListener("change", () => {
    completedItem.classList.remove("checklist__item--invalid");
    if (!completed.checked) confirmed.checked = false;
    onChange();
  });
  confirmed.addEventListener("change", () => {
    confirmedItem.classList.remove("checklist__item--invalid");
    onChange();
  });
  completedItem.append(
    completed,
    element("span", "", "برداشت و Upload تمام طبقات مأموریت تکمیل شده است."),
  );
  confirmedItem.append(
    confirmed,
    element("span", "", "تیم عملیات نتیجه مأموریت را کنترل و تأیید کرده است."),
  );
  section.append(completedItem, confirmedItem);
  const validateDependencies = () => {
    const invalid = confirmed.checked && !completed.checked;
    completedItem.classList.toggle("checklist__item--invalid", invalid);
    return !invalid;
  };
  const validateForSubmit = () => {
    completedItem.classList.toggle(
      "checklist__item--invalid",
      !completed.checked,
    );
    confirmedItem.classList.toggle(
      "checklist__item--invalid",
      !confirmed.checked,
    );
    return completed.checked && confirmed.checked;
  };
  return {
    element: section,
    validateDependencies,
    validateForSubmit,
    getData: () => ({
      missionCompleted: completed.checked,
      operationsConfirmed: confirmed.checked,
    }),
  };
};

export const StageNinePage = ({ pilotId }) => {
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
      element("p", "loading-state", "در حال دریافت وضعیت Upload و G3..."),
    );
    try {
      const [pilot, missions, floors, snapshots] = await Promise.all([
        pilotService.getPilotById(pilotId),
        missionService.getMissions(pilotId),
        dwgService.getFloors(pilotId),
        stageService.getSnapshots(pilotId, 9),
      ]);
      const stage = pilot.stages.find(({ number }) => number === 9);
      if (stage.status === "locked") {
        renderError("Stage 9 تا زمان تأیید Stage 8 قفل است.");
        return;
      }
      const mission = missions.at(-1);
      if (!mission) {
        renderError("مأموریت فعال برای ثبت Upload پیدا نشد.");
        return;
      }
      const incompleteFloors = mission.floorStates.filter(
        ({ capture_state: captureState }) => captureState !== "completed",
      );
      const editable =
        canEdit && ["open", "needs_revision"].includes(stage.status);
      const feedback = element("p", "stage-actions__feedback", notice);
      const back = element("a", "back-link", "بازگشت به جزئیات پرونده");
      const header = element("header", "stage-workspace__header");
      const identity = element("div", "stage-workspace__identity");
      const forms = mission.floorStates.map((state) => {
        const floor = floors.find(({ id }) => id === state.floor_id);
        return floor
          ? uploadForm({
              floor,
              state,
              disabled: !editable,
              onChange: () =>
                setNavigationGuard(() =>
                  window.confirm(
                    "تغییرات Upload ذخیره نشده‌اند. از صفحه خارج می‌شوید؟",
                  ),
                ),
            })
          : null;
      }).filter(Boolean);
      const completion = missionCompletion({
        mission,
        disabled: !editable,
        onChange: () =>
          setNavigationGuard(() =>
            window.confirm(
              "تغییرات تکمیل مأموریت ذخیره نشده‌اند. از صفحه خارج می‌شوید؟",
            ),
          ),
      });
      back.href = `#/pilots/${pilot.id}`;
      identity.append(
        element(
          "span",
          "page-heading__eyebrow",
          `${pilot.code} — ${mission.code} — Stage 9 از ۱۹`,
        ),
        element(
          "h1",
          "page-heading__title",
          "وضعیت Upload در پلتفرم اصلی",
        ),
        element(
          "p",
          "draft-info",
          incompleteFloors.length
            ? `${incompleteFloors.length} طبقه برداشت تکمیل‌شده ندارد و G3 قابل عبور نیست.`
            : "تمام طبقات آماده کنترل Upload و عبور از G3 هستند.",
        ),
      );
      const gate = pilot.gates.find(({ code }) => code === "G3");
      header.append(
        identity,
        element(
          "span",
          "status-badge stage-workspace__status",
          `${STATUS_LABELS[stage.status] ?? stage.status} — G3: ${gate?.status ?? "locked"}`,
        ),
      );
      page.replaceChildren(
        back,
        header,
        feedback,
        ...forms.map(({ element: formElement }) => formElement),
        completion.element,
      );

      if (editable) {
        const actions = element("div", "stage-actions");
        const save = element(
          "button",
          "button button--ghost",
          "ذخیره وضعیت Upload",
        );
        const submit = element(
          "button",
          "button button--primary",
          "ارسال برای بررسی G3",
        );
        save.type = submit.type = "button";
        submit.hidden = !canSubmit;
        const saveAll = async () => {
          const floorValidations = forms.map((form) =>
            form.validateDependencies(),
          );
          if (
            !floorValidations.every(Boolean) ||
            !completion.validateDependencies()
          ) {
            throw new Error(
              "ترتیب موارد قرمزشده Upload یا تأیید عملیات را اصلاح کنید.",
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
          const completionData = completion.getData();
          const times = missionTimes(mission);
          await missionService.saveF03(mission.id, {
            ...mission.formF03,
            mission_completed: completionData.missionCompleted,
            operations_confirmed: completionData.operationsConfirmed,
            started_at: times.startedAt,
            finished_at: completionData.missionCompleted
              ? times.finishedAt
              : null,
          });
          clearNavigationGuard();
          feedback.textContent = "وضعیت Upload و مأموریت ذخیره شد.";
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
          const floorValidations = forms.map((form) =>
            form.validateForSubmit(),
          );
          if (
            incompleteFloors.length ||
            !floorValidations.every(Boolean) ||
            !completion.validateForSubmit()
          ) {
            feedback.textContent =
              "برای G3 تمام طبقات، Upload و تأییدهای قرمزشده باید کامل باشند.";
            return;
          }
          submit.disabled = true;
          try {
            await saveAll();
            await stageService.submit(pilot.id, 9);
            await load("Stage 9 برای بررسی G3 ارسال شد.");
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
            stageNumber: 9,
            title: "بررسی نهایی عملیات G3",
            approveLabel: "تأیید G3 و ورود به Stage 10",
            approvedNotice: "G3 عبور کرد و Stage 10 باز شد.",
            rejectedNotice: "Stage 9 برای اصلاح برگشت داده شد و G3 عبور نکرد.",
            canApprove,
            canReject,
            reload: load,
          }),
        );
      }
      page.append(
        StageSnapshots({
          snapshots,
          title: "نسخه‌های تأییدشده G3",
        }),
      );
    } catch (error) {
      renderError(error.message ?? "دریافت Stage 9 انجام نشد.");
    }
  };
  load();
  return page;
};
