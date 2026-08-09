import { sessionStore } from "../app/sessionStore.js";
import { StageReviewPanel, StageSnapshots, stageElement as element } from "../components/StageShared.js";
import { commercialService } from "../services/commercialService.js";
import { pilotService } from "../services/pilotService.js";
import { stageService } from "../services/stageService.js";
import { formatIranDateTimeLocalValue } from "../utils/jalaliDateTime.js";

const STATUS_LABELS = { open: "باز", submitted: "در انتظار بررسی", approved: "تأییدشده", needs_revision: "نیازمند اصلاح" };
const control = (tag = "input") => { const node = document.createElement(tag); node.className = "stage-form__control"; return node; };
const field = (labelText, input, help = "") => {
  const label = element("label", "stage-form__field");
  label.append(element("span", "stage-form__label", labelText), input);
  if (help) label.append(element("small", "draft-info", help));
  return label;
};
export const StageSeventeenPage = ({ pilotId }) => {
  const page = element("div", "stage-workspace");
  const permissions = sessionStore.getCurrentUser()?.permissions ?? [];
  const canRead = permissions.includes("pilots.read");
  const canManage = permissions.includes("commercial.manage");
  const canSubmit = permissions.includes("checklists.manage");
  const canApprove = permissions.includes("gate_approval.approve");
  const canReject = permissions.includes("gate_approval.reject");
  const renderError = (message) => {
    const state = element("div", "error-state"); const retry = element("button", "button button--primary", "تلاش مجدد");
    retry.type = "button"; retry.addEventListener("click", () => load());
    state.append(element("p", "error-state__message", message), retry); page.replaceChildren(state);
  };

  const load = async (notice = "") => {
    if (!canRead) return renderError("برای مشاهده Stage 17 دسترسی لازم را ندارید.");
    page.replaceChildren(element("p", "loading-state", "در حال دریافت پیشنهاد تجاری..."));
    try {
      const [pilot, proposal, snapshots] = await Promise.all([
        pilotService.getPilotById(pilotId), commercialService.getProposal(pilotId), stageService.getSnapshots(pilotId, 17),
      ]);
      const stage = pilot.stages.find(({ number }) => number === 17);
      if (!stage) return renderError("Stage 17 در ساختار این پرونده وجود ندارد.");
      if (stage.status === "locked" || pilot.currentStage < 17) return renderError("Stage 17 تا تأیید Stage 16 قفل است.");
      const editable = ["open", "needs_revision"].includes(stage.status);
      const feedback = element("p", "stage-actions__feedback", notice);
      const back = element("a", "back-link", "بازگشت به جزئیات پرونده"); back.href = `#/pilots/${pilot.id}`;
      const header = element("header", "stage-workspace__header"); const identity = element("div", "stage-workspace__identity");
      identity.append(
        element("span", "page-heading__eyebrow", `${pilot.code} — Stage 17 از ۱۹`),
        element("h1", "page-heading__title", "تهیه و ارائه پیشنهاد تجاری"),
        element("p", "draft-info", "هدف: ارائه پیشنهاد اختصاصی بر اساس واقعیت استفاده مشتری."),
        element("p", "draft-info", "مسئول: فروش | زمان: حداکثر ۲ روز کاری | ورودی: نتیجه جلسه جمع‌بندی"),
        element("p", "draft-info", "شرط عبور: پیشنهاد دریافت و برای تصمیم‌گیرنده توضیح داده شده و تاریخ پیگیری بعدی ثبت شده باشد."),
      );
      header.append(identity, element("span", "status-badge stage-workspace__status", STATUS_LABELS[stage.status] ?? stage.status));
      page.replaceChildren(back, header, feedback);

      const form = element("section", "stage-form"); const grid = element("div", "stage-form__grid");
      const numberInput = (value) => { const input = control(); input.type = "number"; input.min = "1"; input.value = value ?? ""; return input; };
      const projectCount = numberInput(proposal?.project_count); const floorCount = numberInput(proposal?.floor_count);
      const area = numberInput(proposal?.area_sqm); area.step = "0.01"; const userCount = numberInput(proposal?.user_count);
      const frequency = control(); frequency.value = proposal?.frequency ?? ""; const period = control(); period.value = proposal?.period ?? "";
      const support = control("textarea"); support.rows = 3; support.value = proposal?.support_scope ?? "";
      const features = control("textarea"); features.rows = 3; features.value = (proposal?.features ?? []).join("، ");
      const decisionMaker = control(); decisionMaker.value = proposal?.decision_maker ?? "";
      const followUp = control(); followUp.type = "datetime-local"; followUp.value = formatIranDateTimeLocalValue(proposal?.follow_up_at);
      const inputs = [projectCount, floorCount, area, userCount, frequency, period, support, features, decisionMaker, followUp];
      inputs.forEach((input) => { input.disabled = !editable || !canManage; });
      grid.append(
        field("تعداد پروژه‌ها", projectCount), field("تعداد طبقات", floorCount), field("مساحت کل (مترمربع)", area),
        field("تناوب برداشت", frequency), field("دوره همکاری", period), field("تعداد کاربران", userCount),
        field("سطح پشتیبانی", support), field("امکانات لازم", features, "هر قابلیت را با ویرگول جدا کنید."),
        field("تصمیم‌گیرنده", decisionMaker), field("تاریخ پیگیری بعدی", followUp),
      );
      form.append(
        element("h2", "stage-form__legend", "پیشنهاد اختصاصی مشتری"),
        element("p", "draft-info", "مبنای پیشنهاد: پروژه، طبقه، مساحت، تناوب، دوره همکاری، کاربران، پشتیبانی و امکانات لازم."),
        element("p", "draft-info", "طبق قرارداد جدید بک‌اند و راهنمای اجرایی، ثبت یا بارگذاری فایل PDF برای عبور از این مرحله لازم نیست."),
        grid,
      );
      page.append(form);
      const parsedFeatures = () => features.value.split(/[،,\n]/).map((value) => value.trim()).filter(Boolean);
      const validate = () => {
        [projectCount, floorCount, area, userCount].forEach((input) => input.setAttribute("aria-invalid", String(!input.value || Number(input.value) <= 0)));
        [frequency, period, support, features, decisionMaker].forEach((input) => input.setAttribute("aria-invalid", String(input.value.trim().length < (input === support || input === decisionMaker ? 2 : 1))));
        followUp.setAttribute("aria-invalid", String(!followUp.value));
        return [projectCount, floorCount, area, userCount].every((input) => input.value && Number(input.value) > 0) &&
          frequency.value.trim() && period.value.trim() && support.value.trim().length >= 2 && parsedFeatures().length &&
          decisionMaker.value.trim().length >= 2 && followUp.value;
      };
      const values = () => ({ projectCount: projectCount.value, floorCount: floorCount.value, areaSqm: area.value, frequency: frequency.value.trim(),
        period: period.value.trim(), userCount: userCount.value, supportScope: support.value.trim(), features: parsedFeatures(),
        decisionMaker: decisionMaker.value.trim(), followUpAt: followUp.value });
      if (editable && canManage) {
        const actions = element("div", "stage-actions"); const save = element("button", "button button--ghost", "ذخیره پیشنهاد");
        const submit = element("button", "button button--primary", "ارسال Stage 17 برای بررسی"); save.type = submit.type = "button"; submit.hidden = !canSubmit;
        const persist = async () => { if (!validate()) return false; await commercialService.saveProposal(pilot.id, values()); return true; };
        save.addEventListener("click", async () => { save.disabled = true; try { if (await persist()) await load("پیشنهاد تجاری ذخیره شد."); else save.disabled = false; } catch (error) { feedback.textContent = error.message; save.disabled = false; } });
        submit.addEventListener("click", async () => { submit.disabled = true; try { if (!(await persist())) { submit.disabled = false; return; } await stageService.submit(pilot.id, 17); await load("Stage 17 برای بررسی ارسال شد."); } catch (error) { feedback.textContent = error.message; submit.disabled = false; } });
        actions.append(save, submit); page.append(actions);
      }
      if (stage.status === "submitted" && (canApprove || canReject)) page.append(StageReviewPanel({
        pilotId: pilot.id, stageNumber: 17, title: "بررسی پیشنهاد تجاری", approveLabel: "تأیید و ورود به Stage 18",
        approvedNotice: "Stage 17 تأیید و Stage 18 باز شد.", rejectedNotice: "Stage 17 برای اصلاح بازگردانده شد.", canApprove, canReject, reload: load,
        onApproved: async () => {
          const refreshedPilot = await pilotService.getPilotById(pilot.id);
          if (refreshedPilot.currentStage === 18) {
            window.location.hash = `#/pilots/${pilot.id}/stages/18`;
            return;
          }
          await load("Stage 17 تأیید شد، اما Stage 18 هنوز از سمت سرور فعال نشده است.");
        },
      }));
      page.append(StageSnapshots({ snapshots, title: "نسخه‌های تأییدشده Stage 17" }));
    } catch (error) { renderError(error.message ?? "دریافت Stage 17 انجام نشد."); }
  };
  load(); return page;
};
