import { sessionStore } from "../app/sessionStore.js";
import {
  StageReviewPanel,
  StageSnapshots,
  stageElement as element,
} from "../components/StageShared.js";
import { experienceService } from "../services/experienceService.js";
import { CallsPanel } from "../components/CallsPanel.js";
import { pilotService } from "../services/pilotService.js";
import { stageService } from "../services/stageService.js";
import { formatPersianDateTime } from "../utils/dateFormatter.js";

const STATUS_LABELS = Object.freeze({
  open: "باز",
  submitted: "در انتظار بررسی",
  approved: "تأییدشده",
  needs_revision: "نیازمند اصلاح",
  locked: "قفل‌شده",
});

const DELIVERY_LABELS = Object.freeze({
  delivered: "تحویل‌شده",
  failed: "ناموفق",
  pending: "در انتظار تحویل",
});

const field = (labelText, control) => {
  const label = element("label", "stage-form__field");
  label.append(element("span", "stage-form__label", labelText), control);
  return label;
};

const statusRow = (label, value) => {
  const row = document.createElement("div");
  row.append(element("dt", "", label), element("dd", "", value));
  return row;
};

export const StageElevenPage = ({ pilotId }) => {
  const page = element("div", "stage-workspace");
  const permissions = sessionStore.getCurrentUser()?.permissions ?? [];
  const canRead = permissions.includes("pilots.read");
  const canNotify = permissions.includes("notifications.manage");
  const canSubmit = permissions.includes("checklists.manage");
  const canApprove = permissions.includes("gate_approval.approve");
  const canReject = permissions.includes("gate_approval.reject");
  let latestNotification = null;

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
      renderError("برای مشاهده Stage 11 دسترسی لازم را ندارید.");
      return;
    }
    page.replaceChildren(
      element("p", "loading-state", "در حال دریافت وضعیت اطلاع‌رسانی..."),
    );
    try {
      const [pilot, reference, snapshots] = await Promise.all([
        pilotService.getPilotById(pilotId),
        experienceService.getExternalPlatform(pilotId),
        stageService.getSnapshots(pilotId, 11),
      ]);
      const stage = pilot.stages.find(({ number }) => number === 11);
      if (!stage) {
        renderError("Stage 11 در ساختار این پرونده وجود ندارد.");
        return;
      }
      if (stage.status === "locked" || pilot.currentStage < 11) {
        renderError("Stage 11 تا زمان تأیید Stage 10 قفل است.");
        return;
      }

      const completedBySubmission = ["submitted", "approved"].includes(
        stage.status,
      );
      const deliveryRegistered = completedBySubmission ||
        latestNotification?.status === "delivered" ||
        Boolean(latestNotification?.alternate_contact_method);
      const checks = [
        {
          label: "آماده‌شدن خروجی اصلی ثبت شده است.",
          checked: Boolean(reference?.tour_ready),
        },
        {
          label: "اعلان آماده‌شدن بازدید برای مالک یا مسئول ارسال شده است.",
          checked: completedBySubmission || (latestNotification?.attempts ?? 0) > 0,
        },
        {
          label: "تحویل پیام یا تماس جایگزین ثبت شده است.",
          checked: deliveryRegistered,
        },
      ];
      const feedback = element("p", "stage-actions__feedback", notice);
      const back = element("a", "back-link", "بازگشت به جزئیات پرونده");
      const header = element("header", "stage-workspace__header");
      const identity = element("div", "stage-workspace__identity");
      back.href = `#/pilots/${pilot.id}`;
      identity.append(
        element("span", "page-heading__eyebrow", `${pilot.code} — Stage 11 از ۱۹`),
        element("h1", "page-heading__title", "اطلاع‌رسانی آماده‌شدن بازدید"),
        element(
          "p",
          "draft-info",
          "پیام باید نام پروژه و آماده‌شدن بازدید را اعلام کند. در صورت عدم تحویل، تماس جایگزین همان روز ثبت می‌شود.",
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

      const checklist = document.createElement("fieldset");
      checklist.className = "checklist";
      checklist.append(
        element("legend", "checklist__legend", "شرایط عبور اطلاع‌رسانی"),
      );
      checks.forEach(({ label, checked }) => {
        const item = element(
          "label",
          `checklist__item${checked ? "" : " checklist__item--invalid"}`,
        );
        const checkbox = document.createElement("input");
        checkbox.type = "checkbox";
        checkbox.checked = checked;
        checkbox.disabled = true;
        item.append(checkbox, element("span", "", label));
        checklist.append(item);
      });
      page.replaceChildren(back, header, feedback, checklist);
      page.append(CallsPanel({ pilotId: pilot.id, stageNumber: 11, permissions }));

      if (["open", "needs_revision"].includes(stage.status)) {
        const notificationForm = element("section", "stage-form");
        const grid = element("div", "stage-form__grid");
        const recipientMobile = document.createElement("input");
        const alternateContact = document.createElement("textarea");
        const actions = element("div", "stage-actions");
        const send = element("button", "button button--ghost", "ارسال اعلان");
        const submit = element("button", "button button--primary", "ارسال Stage 11 برای بررسی");
        recipientMobile.className = alternateContact.className = "stage-form__control";
        recipientMobile.type = "tel";
        recipientMobile.inputMode = "numeric";
        recipientMobile.placeholder = "پیش‌فرض: شماره اصلی مالک";
        alternateContact.rows = 3;
        alternateContact.placeholder =
          "فقط در صورت تحویل‌نشدن پیام، روش تماس جایگزین را ثبت کنید.";
        recipientMobile.disabled = alternateContact.disabled = !canNotify;
        send.type = submit.type = "button";
        send.hidden = !canNotify;
        submit.hidden = !canSubmit;
        grid.append(
          field("شماره دریافت‌کننده (اختیاری)", recipientMobile),
          field("روش تماس جایگزین (اختیاری)", alternateContact),
        );
        notificationForm.append(grid);
        send.addEventListener("click", async () => {
          send.disabled = true;
          try {
            latestNotification = await experienceService.sendMainOutputNotification(
              pilot.id,
              {
                recipientMobile: recipientMobile.value,
                alternateContactMethod: alternateContact.value,
              },
            );
            await load(
              latestNotification.status === "delivered"
                ? "اعلان با موفقیت تحویل شد."
                : "ارسال پیام ناموفق بود؛ برای عبور، تماس جایگزین را ثبت کنید.",
            );
          } catch (error) {
            feedback.textContent = error.message;
            send.disabled = false;
          }
        });
        submit.addEventListener("click", async () => {
          submit.disabled = true;
          try {
            await stageService.submit(pilot.id, 11);
            await load("Stage 11 برای بررسی ارسال شد.");
          } catch (error) {
            feedback.textContent = error.message;
            submit.disabled = false;
          }
        });
        actions.append(send, submit);
        page.append(notificationForm, actions);
      }

      if (latestNotification) {
        const result = element("section", "floor-workspace");
        const details = element("dl", "stage-project-summary");
        result.append(element("h2", "stage-form__legend", "نتیجه آخرین ارسال"));
        details.append(
          statusRow(
            "وضعیت تحویل",
            DELIVERY_LABELS[latestNotification.status] ?? latestNotification.status,
          ),
          statusRow("وضعیت سرویس", latestNotification.provider_status),
          statusRow("تعداد تلاش", String(latestNotification.attempts)),
          statusRow("زمان ارسال", formatPersianDateTime(latestNotification.sent_at)),
          statusRow(
            "تماس جایگزین",
            latestNotification.alternate_contact_method || "ثبت نشده",
          ),
          statusRow("خطای ارسال", latestNotification.last_error || "ندارد"),
        );
        result.append(details);
        page.append(result);
      }

      if (stage.status === "submitted" && (canApprove || canReject)) {
        page.append(
          StageReviewPanel({
            pilotId: pilot.id,
            stageNumber: 11,
            title: "بررسی اطلاع‌رسانی Stage 11",
            approveLabel: "تأیید و ورود به Stage 12",
            approvedNotice: "Stage 11 تأیید شد و Stage 12 باز شد.",
            rejectedNotice: "Stage 11 برای اصلاح برگشت داده شد.",
            canApprove,
            canReject,
            reload: load,
            onApproved: async () => {
              const refreshedPilot = await pilotService.getPilotById(pilot.id);
              if (refreshedPilot.currentStage === 12) {
                window.location.hash = `#/pilots/${pilot.id}/stages/12`;
                return;
              }
              await load(
                "Stage 11 تأیید شد، اما Stage 12 هنوز از سمت سرور فعال نشده است.",
              );
            },
          }),
        );
      }
      page.append(StageSnapshots({ snapshots, title: "نسخه‌های تأییدشده Stage 11" }));
    } catch (error) {
      renderError(error.message ?? "دریافت Stage 11 انجام نشد.");
    }
  };
  load();
  return page;
};
