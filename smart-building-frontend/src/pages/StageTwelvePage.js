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

const TRAINING_ITEMS = Object.freeze([
  ["loginAndProject", "ورود به حساب و انتخاب پروژه انجام شد."],
  ["floorAndPlan", "انتخاب طبقه و مشاهده نقشه آموزش داده شد."],
  ["tourAndNavigation", "ورود به تور و حرکت در مسیر تمرین شد."],
  ["capabilitiesIntroduced", "امکانات موردنیاز مالک معرفی شد."],
  ["supportIntroduced", "روش دریافت پشتیبانی اعلام شد."],
  ["independentUse", "مالک توانست یک بار مستقل عملیات اصلی را انجام دهد."],
]);

const trainingValues = (form) => ({
  loginAndProject: Boolean(form?.login_trained && form?.project_trained),
  floorAndPlan: Boolean(form?.floor_trained && form?.plan_trained),
  tourAndNavigation: Boolean(form?.tour_trained && form?.navigation_trained),
  capabilitiesIntroduced: Boolean(form?.training_completed),
  supportIntroduced: Boolean(form?.support_trained),
  independentUse: Boolean(form?.independent_use_confirmed),
});

const trainingForm = ({ form, disabled }) => {
  const checklist = document.createElement("fieldset");
  const items = new Map();
  const initial = trainingValues(form);
  checklist.className = "checklist";
  checklist.append(
    element("legend", "checklist__legend", "چک‌لیست آموزش اولیه مالک"),
  );
  TRAINING_ITEMS.forEach(([key, label]) => {
    const item = element("label", "checklist__item");
    const checkbox = document.createElement("input");
    checkbox.type = "checkbox";
    checkbox.checked = initial[key];
    checkbox.disabled = disabled;
    checkbox.addEventListener("change", () =>
      item.classList.remove("checklist__item--invalid"),
    );
    item.append(checkbox, element("span", "", label));
    checklist.append(item);
    items.set(key, { checkbox, item });
  });
  const getData = () => Object.fromEntries(
    [...items].map(([key, { checkbox }]) => [key, checkbox.checked]),
  );
  const validate = () => {
    let valid = true;
    items.forEach(({ checkbox, item }) => {
      const invalid = !checkbox.checked;
      item.classList.toggle("checklist__item--invalid", invalid);
      valid = valid && !invalid;
    });
    return valid;
  };
  return { element: checklist, getData, validate };
};

export const StageTwelvePage = ({ pilotId }) => {
  const page = element("div", "stage-workspace");
  const permissions = sessionStore.getCurrentUser()?.permissions ?? [];
  const canRead = permissions.includes("pilots.read");
  const canEdit = permissions.includes("customer_success.manage");
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
      renderError("برای مشاهده Stage 12 دسترسی لازم را ندارید.");
      return;
    }
    page.replaceChildren(
      element("p", "loading-state", "در حال دریافت اطلاعات آموزش مالک..."),
    );
    try {
      const [pilot, formF04, snapshots] = await Promise.all([
        pilotService.getPilotById(pilotId),
        experienceService.getF04(pilotId),
        stageService.getSnapshots(pilotId, 12),
      ]);
      const stage = pilot.stages.find(({ number }) => number === 12);
      if (!stage) {
        renderError("Stage 12 در ساختار این پرونده وجود ندارد.");
        return;
      }
      if (stage.status === "locked" || pilot.currentStage < 12) {
        renderError("Stage 12 تا زمان تأیید Stage 11 قفل است.");
        return;
      }

      const editable = canEdit && ["open", "needs_revision"].includes(stage.status);
      const feedback = element("p", "stage-actions__feedback", notice);
      const back = element("a", "back-link", "بازگشت به جزئیات پرونده");
      const header = element("header", "stage-workspace__header");
      const identity = element("div", "stage-workspace__identity");
      const form = trainingForm({ form: formF04, disabled: !editable });
      back.href = `#/pilots/${pilot.id}`;
      identity.append(
        element("span", "page-heading__eyebrow", `${pilot.code} — Stage 12 از ۱۹`),
        element("h1", "page-heading__title", "آموزش اولیه مالک"),
        element(
          "p",
          "draft-info",
          "آموزش کوتاه و عملی، حداکثر ظرف ۲۴ ساعت و به‌صورت تلفنی، آنلاین یا حضوری انجام می‌شود.",
        ),
        element(
          "p",
          "draft-info",
          "شرط عبور: مالک بتواند یک بار مستقل عملیات اصلی را انجام دهد.",
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
        const save = element("button", "button button--ghost", "ذخیره آموزش");
        const submit = element("button", "button button--primary", "ارسال Stage 12 برای بررسی");
        save.type = submit.type = "button";
        save.hidden = !canEdit;
        submit.hidden = !canSubmit;
        save.addEventListener("click", async () => {
          save.disabled = true;
          try {
            await experienceService.saveF04Training(pilot.id, form.getData());
            await load("اطلاعات آموزش مالک ذخیره شد.");
          } catch (error) {
            feedback.textContent = error.message;
            save.disabled = false;
          }
        });
        submit.addEventListener("click", async () => {
          if (!form.validate()) return;
          submit.disabled = true;
          try {
            if (canEdit) {
              await experienceService.saveF04Training(pilot.id, form.getData());
            }
            await stageService.submit(pilot.id, 12);
            await load("Stage 12 برای بررسی ارسال شد.");
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
            stageNumber: 12,
            title: "بررسی آموزش اولیه مالک",
            approveLabel: "تأیید و ورود به Stage 13",
            approvedNotice: "Stage 12 تأیید شد و Stage 13 باز شد.",
            rejectedNotice: "Stage 12 برای اصلاح برگشت داده شد.",
            canApprove,
            canReject,
            reload: load,
          }),
        );
      }
      page.append(StageSnapshots({ snapshots, title: "نسخه‌های تأییدشده Stage 12" }));
    } catch (error) {
      renderError(error.message ?? "دریافت Stage 12 انجام نشد.");
    }
  };
  load();
  return page;
};
