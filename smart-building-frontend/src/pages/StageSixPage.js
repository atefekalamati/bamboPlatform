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

const READINESS_ITEMS = Object.freeze([
  {
    key: "site_entry_confirmed",
    label: "ورود کارشناس به محل پروژه و حضور در نقطه هماهنگ‌شده تأیید شد.",
  },
  {
    key: "permission_confirmed",
    label: "مجوز ورود و انجام برداشت از مسئول محل دریافت شده است.",
  },
  {
    key: "ppe_ready",
    label: "تجهیزات حفاظت فردی موردنیاز آماده و کنترل شده است.",
  },
  {
    key: "camera_ready",
    label: "دوربین و تجهیزات برداشت سالم و آماده استفاده هستند.",
  },
  {
    key: "main_app_connected",
    label: "اتصال کارشناس به پروژه در اپلیکیشن اصلی آزمایش شده است.",
  },
  {
    key: "battery_ready",
    label: "شارژ باتری تجهیزات برای انجام مأموریت کافی است.",
  },
  {
    key: "storage_ready",
    label: "فضای ذخیره‌سازی موردنیاز کنترل شده و کافی است.",
  },
  {
    key: "project_floor_plan_confirmed",
    label: "پلان و طبقات مأموریت با پروژه اصلی تطبیق داده شده‌اند.",
  },
  {
    key: "test_image_completed",
    label: "تصویر آزمایشی گرفته و کیفیت آن پیش از شروع برداشت کنترل شده است.",
  },
]);

const readinessForm = ({ initialData, disabled, onChange }) => {
  const form = document.createElement("form");
  const checklist = document.createElement("fieldset");
  const items = new Map();
  const stopField = element("div", "stage-form__field");
  const stopLabel = element(
    "label",
    "stage-form__label",
    "مانع شروع مأموریت (در صورت وجود)",
  );
  const stopReason = document.createElement("textarea");
  const stopHint = element(
    "p",
    "draft-info",
    "اگر مانعی وجود دارد آن را ثبت کنید. تا زمان رفع مانع و خالی‌شدن این فیلد، مرحله قابل ارسال نیست.",
  );

  form.className = "stage-form";
  checklist.className = "checklist";
  checklist.append(
    element("legend", "checklist__legend", "چک‌لیست آمادگی قبل از برداشت"),
  );
  READINESS_ITEMS.forEach(({ key, label }) => {
    const item = element("label", "checklist__item");
    const checkbox = document.createElement("input");
    checkbox.type = "checkbox";
    checkbox.checked = Boolean(initialData[key]);
    checkbox.disabled = disabled;
    checkbox.addEventListener("change", () => {
      item.classList.remove("checklist__item--invalid");
      onChange();
    });
    item.append(checkbox, element("span", "", label));
    checklist.append(item);
    items.set(key, { checkbox, item });
  });

  stopLabel.htmlFor = "stage6-stop-reason";
  stopReason.id = "stage6-stop-reason";
  stopReason.className = "stage-form__control";
  stopReason.value = initialData.stop_condition_reason ?? "";
  stopReason.disabled = disabled;
  stopReason.addEventListener("input", () => {
    stopReason.removeAttribute("aria-invalid");
    onChange();
  });
  stopField.append(stopLabel, stopReason, stopHint);
  form.append(checklist, stopField);

  return {
    element: form,
    getData: () => ({
      ...initialData,
      ...Object.fromEntries(
        [...items].map(([key, { checkbox }]) => [key, checkbox.checked]),
      ),
      stop_condition_reason: stopReason.value.trim() || null,
    }),
    validate: () => {
      let valid = true;
      items.forEach(({ checkbox, item }) => {
        item.classList.toggle(
          "checklist__item--invalid",
          !checkbox.checked,
        );
        valid = valid && checkbox.checked;
      });
      const hasStopCondition = Boolean(stopReason.value.trim());
      stopReason.setAttribute("aria-invalid", String(hasStopCondition));
      return valid && !hasStopCondition;
    },
  };
};

export const StageSixPage = ({ pilotId }) => {
  const page = element("div", "stage-workspace");
  const user = sessionStore.getCurrentUser();
  const permissions = user?.permissions ?? [];
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
      element("p", "loading-state", "در حال دریافت چک‌لیست Stage 6..."),
    );
    try {
      const [pilot, missions, snapshots] = await Promise.all([
        pilotService.getPilotById(pilotId),
        missionService.getMissions(pilotId),
        stageService.getSnapshots(pilotId, 6),
      ]);
      const stage = pilot.stages.find(({ number }) => number === 6);
      if (stage.status === "locked") {
        renderError("Stage 6 تا زمان تأیید Stage 5 قفل است.");
        return;
      }
      const mission = missions.at(-1);
      if (!mission) {
        renderError("برای این پرونده هنوز مأموریت معتبری ثبت نشده است.");
        return;
      }
      const editable =
        canEdit && ["open", "needs_revision"].includes(stage.status);
      const back = element("a", "back-link", "بازگشت به جزئیات پرونده");
      const header = element("header", "stage-workspace__header");
      const identity = element("div", "stage-workspace__identity");
      const feedback = element("p", "stage-actions__feedback", notice);
      const form = readinessForm({
        initialData: mission.formF03,
        disabled: !editable,
        onChange: () =>
          setNavigationGuard(() =>
            window.confirm(
              "تغییرات چک‌لیست ذخیره نشده‌اند. از صفحه خارج می‌شوید؟",
            ),
          ),
      });
      back.href = `#/pilots/${pilot.id}`;
      identity.append(
        element(
          "span",
          "page-heading__eyebrow",
          `${pilot.code} — ${mission.code} — Stage 6 از ۱۹`,
        ),
        element("h1", "page-heading__title", "آمادگی قبل از برداشت"),
        element(
          "p",
          "draft-info",
          "این کنترل‌ها باید در محل پروژه و پیش از شروع برداشت انجام شوند.",
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
      page.replaceChildren(back, header, feedback, form.element);

      if (editable) {
        const actions = element("div", "stage-actions");
        const save = element(
          "button",
          "button button--ghost",
          "ذخیره چک‌لیست",
        );
        const submit = element(
          "button",
          "button button--primary",
          "ارسال Stage 6 برای بررسی",
        );
        save.type = submit.type = "button";
        submit.hidden = !canSubmit;
        const saveForm = async () => {
          save.disabled = true;
          await missionService.saveF03(mission.id, form.getData());
          clearNavigationGuard();
          feedback.textContent = "چک‌لیست آمادگی در دیتابیس ذخیره شد.";
          save.disabled = false;
        };
        save.addEventListener("click", async () => {
          try {
            await saveForm();
          } catch (error) {
            feedback.textContent = error.message;
            save.disabled = false;
          }
        });
        submit.addEventListener("click", async () => {
          if (!form.validate()) {
            feedback.textContent =
              "موارد قرمزشده باید تأیید شوند و مانع شروع نباید باقی مانده باشد.";
            return;
          }
          submit.disabled = true;
          try {
            await saveForm();
            await stageService.submit(pilot.id, 6);
            await load("Stage 6 برای بررسی ارسال شد.");
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
            stageNumber: 6,
            title: "بررسی آمادگی قبل از برداشت",
            approveLabel: "تأیید و ورود به Stage 7",
            approvedNotice: "Stage 6 تأیید شد و Stage 7 باز شد.",
            rejectedNotice: "Stage 6 برای اصلاح برگشت داده شد.",
            canApprove,
            canReject,
            reload: load,
          }),
        );
      }
      page.append(
        StageSnapshots({
          snapshots,
          title: "نسخه‌های تأییدشده Stage 6",
        }),
      );
    } catch (error) {
      renderError(error.message ?? "دریافت Stage 6 انجام نشد.");
    }
  };
  load();
  return page;
};
