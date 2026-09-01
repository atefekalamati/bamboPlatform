import { sessionStore } from "../app/sessionStore.js";
import { StageReviewPanel, StageSnapshots, stageElement as element } from "../components/StageShared.js";
import { evaluationService } from "../services/evaluationService.js";
import { pilotService } from "../services/pilotService.js";
import { stageService } from "../services/stageService.js";

const DIMENSIONS = Object.freeze([
  ["operations", "عملیات", "نتیجه اجرای برداشت، بارگذاری و زمان‌بندی عملیات را بر پایه شواهد ثبت کنید."],
  ["quality", "کیفیت", "کیفیت خروجی، پوشش فضا و خطاهای مشاهده‌شده را جمع‌بندی کنید."],
  ["technical", "فنی", "وضعیت پردازش، مسیر، اتصال Plan و آمادگی بازدید را ارزیابی کنید."],
  ["customer", "مشتری", "تجربه مشاهده، آموزش، رضایت و ارزش درک‌شده مشتری را ثبت کنید."],
  ["commercial", "تجاری", "تمایل به ادامه، آمادگی پیشنهاد و موانع تصمیم‌گیری را ارزیابی کنید."],
]);
const EVIDENCE = Object.freeze([
  ["actual_progress", "پیشرفت واقعی پروژه"],
  ["manager_audio_report", "گزارش صوتی مدیر پروژه"],
]);
const STATUS_LABELS = { open: "باز", submitted: "در انتظار بررسی", approved: "تأییدشده", needs_revision: "نیازمند اصلاح" };

const control = (tag = "input") => {
  const node = document.createElement(tag);
  node.className = "stage-form__control";
  return node;
};
const field = (labelText, input, help = "") => {
  const label = element("label", "stage-form__field");
  label.append(element("span", "stage-form__label", labelText), input);
  if (help) label.append(element("small", "draft-info", help));
  return label;
};
export const StageFifteenPage = ({ pilotId }) => {
  const page = element("div", "stage-workspace");
  const permissions = sessionStore.getCurrentUser()?.permissions ?? [];
  const canRead = permissions.includes("pilots.read");
  const canManage = permissions.includes("pilots.manage");
  const canEvidence = permissions.includes("customer_success.manage");
  const canSubmit = permissions.includes("checklists.manage");
  const canApprove = permissions.includes("gate_approval.approve");
  const canReject = permissions.includes("gate_approval.reject");

  const renderError = (message) => {
    const state = element("div", "error-state");
    const retry = element("button", "button button--primary", "تلاش مجدد");
    retry.type = "button";
    retry.addEventListener("click", () => load());
    state.append(element("p", "error-state__message", message), retry);
    page.replaceChildren(state);
  };

  const load = async (notice = "") => {
    if (!canRead) return renderError("برای مشاهده Stage 15 دسترسی لازم را ندارید.");
    page.replaceChildren(element("p", "loading-state", "در حال دریافت ارزیابی موفقیت پایلوت..."));
    try {
      const [pilot, evaluation, evidenceRows, snapshots] = await Promise.all([
        pilotService.getPilotById(pilotId), evaluationService.getEvaluation(pilotId),
        evaluationService.getExternalEvidence(pilotId), stageService.getSnapshots(pilotId, 15),
      ]);
      const stage = pilot.stages.find(({ number }) => number === 15);
      if (!stage) return renderError("Stage 15 در ساختار این پرونده وجود ندارد.");
      if (stage.status === "locked" || pilot.currentStage < 15) {
        return renderError("Stage 15 تا تأیید Stage 14 قفل است.");
      }
      const editable = ["open", "needs_revision"].includes(stage.status);
      const feedback = element("p", "stage-actions__feedback", notice);
      const back = element("a", "back-link", "بازگشت به جزئیات پرونده");
      back.href = `#/pilots/${pilot.id}`;
      const header = element("header", "stage-workspace__header");
      const identity = element("div", "stage-workspace__identity");
      identity.append(
        element("span", "page-heading__eyebrow", `${pilot.code} — Stage 15 از ۱۹`),
        element("h1", "page-heading__title", "ارزیابی موفقیت پایلوت"),
        element("p", "draft-info", "هدف: سنجش عملیات، تجربه مشتری و آمادگی تجاری بر پایه شواهد."),
        element("p", "draft-info", "مسئول: مدیر پایلوت | زمان: تا ۲ روز پس از آخرین خروجی | ورودی: KPI و بازخورد"),
        element("p", "draft-info", "شرط عبور: گزارش یک‌صفحه‌ای شامل نتیجه، شواهد، مشکلات و پیشنهاد ادامه تهیه شده باشد."),
      );
      header.append(identity, element("span", "status-badge stage-workspace__status", STATUS_LABELS[stage.status] ?? stage.status));
      page.replaceChildren(back, header, feedback);

      const evidenceMap = new Map(evidenceRows.map((row) => [row.capability, row]));
      const evidenceSection = element("section", "stage-form");
      evidenceSection.append(
        element("h2", "stage-form__legend", "شواهد KPI موجود در پلتفرم اصلی"),
        element("p", "draft-info", "فایل یا رسانه در این سامانه کپی نمی‌شود؛ فقط نتیجه بررسی شواهد موجود ثبت می‌شود."),
      );
      const evidenceControls = new Map();
      EVIDENCE.forEach(([capability, label]) => {
        const current = evidenceMap.get(capability);
        const grid = element("div", "stage-form__grid");
        const status = control("select");
        [["", "انتخاب وضعیت"], ["checked", "بررسی شد"], ["mismatch", "مغایرت دارد"], ["unavailable", "در دسترس نیست"], ["not_checked", "بررسی نشده"]]
          .forEach(([value, text]) => status.add(new Option(text, value)));
        status.value = current?.status ?? "";
        const checkedAt = control();
        checkedAt.type = "datetime-local";
        checkedAt.value = current?.checked_at ? current.checked_at.slice(0, 16) : "";
        const result = control("textarea");
        result.rows = 2;
        result.value = current?.result ?? "";
        [status, checkedAt, result].forEach((input) => { input.disabled = !editable || !canEvidence; });
        grid.append(field(`${label}: وضعیت`, status), field("زمان بررسی", checkedAt), field("نتیجه/شاهد", result));
        evidenceSection.append(grid);
        evidenceControls.set(capability, { status, checkedAt, result });
      });
      page.append(evidenceSection);

      const form = element("section", "stage-form");
      form.append(element("h2", "stage-form__legend", "ارزیابی پنج‌بُعدی"));
      const dimensionControls = new Map();
      DIMENSIONS.forEach(([key, label, help]) => {
        const grid = element("div", "stage-form__grid");
        const status = control("select");
        [["", "انتخاب وضعیت"], ["approved", "تأیید"], ["needs_action", "نیازمند اقدام"], ["not_applicable", "نامرتبط"]]
          .forEach(([value, text]) => status.add(new Option(text, value)));
        status.value = evaluation?.[`${key}_status`] ?? "";
        const result = control("textarea");
        result.rows = 3;
        result.value = evaluation?.[`${key}_result`] ?? "";
        status.disabled = result.disabled = !editable || !canManage;
        grid.append(field(`وضعیت ${label}`, status), field(`نتیجه ${label}`, result, help));
        form.append(grid);
        dimensionControls.set(key, { status, result });
      });
      const summary = control("textarea");
      summary.rows = 8;
      summary.value = evaluation?.one_page_summary ?? "";
      summary.placeholder = "نتیجه کلی، شواهد کلیدی، مشکلات و پیشنهاد ادامه را در یک گزارش جمع‌بندی کنید.";
      summary.disabled = !editable || !canManage;
      form.append(field("گزارش یک‌صفحه‌ای", summary, "گزارش باید هر چهار بخش نتیجه، شواهد، مشکلات و پیشنهاد ادامه را پوشش دهد."));
      page.append(form);

      const validate = () => {
        let valid = true;
        dimensionControls.forEach(({ status, result }) => {
          status.setAttribute("aria-invalid", String(!status.value));
          result.setAttribute("aria-invalid", String(result.value.trim().length < 2));
          valid = valid && Boolean(status.value) && result.value.trim().length >= 2;
        });
        summary.setAttribute("aria-invalid", String(summary.value.trim().length < 2));
        return valid && summary.value.trim().length >= 2;
      };
      const values = () => Object.fromEntries([
        ...[...dimensionControls].flatMap(([key, { status, result }]) => [
          [`${key}Status`, status.value], [`${key}Result`, result.value.trim()],
        ]),
        ["onePageSummary", summary.value.trim()],
      ]);
      const saveAll = async () => {
        if (!validate()) return false;
        if (canEvidence) {
          for (const [capability, inputs] of evidenceControls) {
            const exceptionNeedsResult = ["mismatch", "unavailable"].includes(inputs.status.value) && !inputs.result.value.trim();
            inputs.status.setAttribute("aria-invalid", String(!inputs.status.value));
            inputs.checkedAt.setAttribute("aria-invalid", String(!inputs.checkedAt.value));
            inputs.result.setAttribute("aria-invalid", String(exceptionNeedsResult));
            if (!inputs.status.value || !inputs.checkedAt.value || exceptionNeedsResult) return false;
            await evaluationService.saveExternalEvidence(pilot.id, capability, {
              status: inputs.status.value, checkedAt: inputs.checkedAt.value, result: inputs.result.value,
            });
          }
        }
        await evaluationService.saveEvaluation(pilot.id, values());
        return true;
      };
      if (editable && canManage) {
        const actions = element("div", "stage-actions");
        const save = element("button", "button button--ghost", "ذخیره ارزیابی");
        const submit = element("button", "button button--primary", "ارسال Stage 15 برای بررسی");
        save.type = submit.type = "button";
        submit.hidden = !canSubmit;
        save.addEventListener("click", async () => {
          save.disabled = true;
          try { if (await saveAll()) await load("ارزیابی و شواهد Stage 15 ذخیره شد."); }
          catch (error) { feedback.textContent = error.message; save.disabled = false; }
        });
        submit.addEventListener("click", async () => {
          submit.disabled = true;
          try {
            if (!(await saveAll())) { submit.disabled = false; return; }
            await stageService.submit(pilot.id, 15);
            await load("Stage 15 برای بررسی و عبور از G5 ارسال شد.");
          } catch (error) { feedback.textContent = error.message; submit.disabled = false; }
        });
        actions.append(save, submit);
        page.append(actions);
      }
      if (stage.status === "submitted" && (canApprove || canReject)) {
        page.append(StageReviewPanel({
          pilotId: pilot.id, stageNumber: 15, title: "بررسی ارزیابی موفقیت پایلوت — G5",
          approveLabel: "تأیید G5 و ورود به Stage 16",
          approvedNotice: "G5 تأیید شد و Stage 16 باز شد.",
          rejectedNotice: "Stage 15 برای اصلاح بازگردانده شد.",
          canApprove, canReject, reload: load,
          onApproved: async () => {
            const refreshedPilot = await pilotService.getPilotById(pilot.id);
            if (refreshedPilot.currentStage === 16) {
              window.location.hash = `#/pilots/${pilot.id}/stages/16`;
              return;
            }
            await load("G5 تأیید شد، اما Stage 16 هنوز از سمت سرور فعال نشده است.");
          },
        }));
      }
      page.append(StageSnapshots({ snapshots, title: "نسخه‌های تأییدشده Stage 15" }));
    } catch (error) { renderError(error.message ?? "دریافت Stage 15 انجام نشد."); }
  };
  load();
  return page;
};
