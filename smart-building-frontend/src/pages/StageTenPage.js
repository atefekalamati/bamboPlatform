import { sessionStore } from "../app/sessionStore.js";
import {
  StageReviewPanel,
  StageSnapshots,
  stageElement as element,
} from "../components/StageShared.js";
import { experienceService } from "../services/experienceService.js";
import { pilotService } from "../services/pilotService.js";
import { stageService } from "../services/stageService.js";

const STATUS_LABELS = Object.freeze({
  open: "باز",
  submitted: "در انتظار بررسی",
  approved: "تأییدشده",
  needs_revision: "نیازمند اصلاح",
  locked: "قفل‌شده",
});

const PLATFORM_STATUS_LABELS = Object.freeze({
  available: "در دسترس",
  degraded: "دارای اختلال",
  down: "خارج از دسترس",
  unknown: "نامشخص",
});

const CHECKS = Object.freeze([
  ["processingStarted", "پردازش در پلتفرم اصلی شروع شده است."],
  ["routeDetected", "مسیر حرکت تشخیص داده شده است."],
  ["planConnected", "خروجی به Plan صحیح متصل شده است."],
  ["tourReady", "وضعیت بازدید در پلتفرم اصلی آماده است."],
  ["capturesMenuChecked", "منوی برداشت‌ها در پلتفرم اصلی بررسی شده است."],
  ["latestCaptureChecked", "وضعیت آخرین برداشت بررسی شده است."],
  ["lastVisitChecked", "آخرین بازدید پروژه بررسی شده است."],
]);

const toDateTimeLocal = (value) => {
  const date = value ? new Date(`${value}${/[zZ]|[+-]\d{2}:\d{2}$/.test(value) ? "" : "Z"}`) : new Date();
  const local = new Date(date.getTime() - date.getTimezoneOffset() * 60_000);
  return local.toISOString().slice(0, 16);
};

const field = (labelText, control) => {
  const label = element("label", "stage-form__field");
  label.append(element("span", "stage-form__label", labelText), control);
  return label;
};

const platformForm = ({ reference, disabled }) => {
  const form = element("section", "stage-form");
  const grid = element("div", "stage-form__grid");
  const projectReference = document.createElement("input");
  const platformStatus = document.createElement("select");
  const checkedAt = document.createElement("input");
  const reason = document.createElement("textarea");
  const checklist = document.createElement("fieldset");
  const items = new Map();

  projectReference.className = platformStatus.className =
    checkedAt.className = reason.className = "stage-form__control";
  projectReference.type = "text";
  projectReference.placeholder = "شناسه پروژه در پلتفرم اصلی (نه URL)";
  projectReference.value = reference?.project_reference ?? "";
  Object.entries(PLATFORM_STATUS_LABELS).forEach(([value, label]) =>
    platformStatus.add(new Option(label, value)),
  );
  platformStatus.value = reference?.platform_status ?? "unknown";
  checkedAt.type = "datetime-local";
  checkedAt.value = toDateTimeLocal(reference?.checked_at);
  reason.rows = 3;
  reason.placeholder = "در صورت اختلال، علت را ثبت کنید.";
  reason.value = reference?.reason ?? "";
  projectReference.disabled = platformStatus.disabled =
    checkedAt.disabled = reason.disabled = disabled;

  checklist.className = "checklist";
  checklist.append(
    element("legend", "checklist__legend", "کنترل نتیجه پردازش در پلتفرم اصلی"),
  );
  CHECKS.forEach(([key, label]) => {
    const item = element("label", "checklist__item");
    const checkbox = document.createElement("input");
    const apiKey = key.replace(/[A-Z]/g, (letter) => `_${letter.toLowerCase()}`);
    checkbox.type = "checkbox";
    checkbox.checked = Boolean(reference?.[apiKey]);
    checkbox.disabled = disabled;
    checkbox.addEventListener("change", () =>
      item.classList.remove("checklist__item--invalid"),
    );
    item.append(checkbox, element("span", "", label));
    checklist.append(item);
    items.set(key, { checkbox, item });
  });

  grid.append(
    field("شناسه پروژه در پلتفرم اصلی", projectReference),
    field("وضعیت پلتفرم اصلی", platformStatus),
    field("زمان آخرین کنترل", checkedAt),
    field("علت یا توضیح وضعیت", reason),
  );
  form.append(grid, checklist);

  const getData = () => ({
    projectReference: projectReference.value,
    platformStatus: platformStatus.value,
    checkedAt: checkedAt.value,
    reason: reason.value,
    ...Object.fromEntries(
      [...items].map(([key, { checkbox }]) => [key, checkbox.checked]),
    ),
  });
  const validate = ({ forSubmit = false } = {}) => {
    const values = getData();
    const referenceInvalid = Boolean(values.projectReference.trim()) &&
      /^https?:\/\//i.test(values.projectReference.trim());
    const timeInvalid = !values.checkedAt;
    const reasonInvalid = values.platformStatus !== "available" &&
      !values.reason.trim();
    projectReference.setAttribute("aria-invalid", String(referenceInvalid));
    checkedAt.setAttribute("aria-invalid", String(timeInvalid));
    reason.setAttribute("aria-invalid", String(reasonInvalid));
    let checksValid = true;
    items.forEach(({ checkbox, item }) => {
      const invalid = forSubmit && !checkbox.checked;
      item.classList.toggle("checklist__item--invalid", invalid);
      checksValid = checksValid && !invalid;
    });
    return !referenceInvalid && !timeInvalid && !reasonInvalid && checksValid;
  };
  return { element: form, getData, validate };
};

export const StageTenPage = ({ pilotId }) => {
  const page = element("div", "stage-workspace");
  const permissions = sessionStore.getCurrentUser()?.permissions ?? [];
  const canRead = permissions.includes("pilots.read");
  const canEdit = permissions.includes("external_status.manage");
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
    if (!canRead) {
      renderError("برای مشاهده Stage 10 دسترسی لازم را ندارید.");
      return;
    }
    page.replaceChildren(
      element("p", "loading-state", "در حال دریافت وضعیت پردازش..."),
    );
    try {
      const [pilot, reference, snapshots] = await Promise.all([
        pilotService.getPilotById(pilotId),
        experienceService.getExternalPlatform(pilotId),
        stageService.getSnapshots(pilotId, 10),
      ]);
      const stage = pilot.stages.find(({ number }) => number === 10);
      if (!stage) {
        renderError("Stage 10 در ساختار این پرونده وجود ندارد.");
        return;
      }
      if (stage.status === "locked" || pilot.currentStage < 10) {
        renderError("Stage 10 تا زمان تأیید Stage 9 و عبور از G3 قفل است.");
        return;
      }

      const editable = canEdit && ["open", "needs_revision"].includes(stage.status);
      const feedback = element("p", "stage-actions__feedback", notice);
      const back = element("a", "back-link", "بازگشت به جزئیات پرونده");
      const header = element("header", "stage-workspace__header");
      const identity = element("div", "stage-workspace__identity");
      const form = platformForm({ reference, disabled: !editable });
      back.href = `#/pilots/${pilot.id}`;
      identity.append(
        element("span", "page-heading__eyebrow", `${pilot.code} — Stage 10 از ۱۹`),
        element("h1", "page-heading__title", "کنترل پردازش در پلتفرم اصلی"),
        element(
          "p",
          "draft-info",
          "در این مرحله فقط نتیجه عملیات پلتفرم اصلی ثبت می‌شود؛ پردازش و ساخت بازدید در این سامانه انجام نمی‌شود.",
        ),
      );
      header.append(
        identity,
        element(
          "span",
          "status-badge stage-workspace__status",
          `${STATUS_LABELS[stage.status] ?? stage.status} — مرحله جاری: ${pilot.currentStage}`,
        ),
      );
      page.replaceChildren(back, header, feedback, form.element);

      if (["open", "needs_revision"].includes(stage.status)) {
        const actions = element("div", "stage-actions");
        const save = element("button", "button button--ghost", "ذخیره وضعیت");
        const submit = element("button", "button button--primary", "ارسال Stage 10 برای بررسی");
        save.type = submit.type = "button";
        save.hidden = !canEdit;
        submit.hidden = !canSubmit;
        save.addEventListener("click", async () => {
          if (!form.validate()) return;
          save.disabled = true;
          try {
            await experienceService.saveExternalPlatform(pilot.id, form.getData());
            await load("وضعیت پلتفرم اصلی ذخیره شد.");
          } catch (error) {
            feedback.textContent = error.message;
            save.disabled = false;
          }
        });
        submit.addEventListener("click", async () => {
          if (!form.validate({ forSubmit: true })) return;
          submit.disabled = true;
          try {
            if (canEdit) {
              await experienceService.saveExternalPlatform(pilot.id, form.getData());
            }
            await stageService.submit(pilot.id, 10);
            await load("Stage 10 برای بررسی ارسال شد.");
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
            stageNumber: 10,
            title: "بررسی نتیجه پردازش Stage 10",
            approveLabel: "تأیید و ورود به Stage 11",
            approvedNotice: "Stage 10 تأیید شد و Stage 11 باز شد.",
            rejectedNotice: "Stage 10 برای اصلاح برگشت داده شد.",
            canApprove,
            canReject,
            reload: load,
            onApproved: async () => {
              const refreshedPilot = await pilotService.getPilotById(pilot.id);
              if (refreshedPilot.currentStage === 11) {
                window.location.hash = `#/pilots/${pilot.id}/stages/11`;
                return;
              }
              await load(
                "Stage 10 تأیید شد، اما Stage 11 هنوز از سمت سرور فعال نشده است.",
              );
            },
          }),
        );
      }
      page.append(StageSnapshots({ snapshots, title: "نسخه‌های تأییدشده Stage 10" }));
    } catch (error) {
      renderError(error.message ?? "دریافت Stage 10 انجام نشد.");
    }
  };
  load();
  return page;
};
