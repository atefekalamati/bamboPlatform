import { sessionStore } from "../app/sessionStore.js";
import { StageReviewPanel, StageSnapshots, stageElement as element } from "../components/StageShared.js";
import { experienceService } from "../services/experienceService.js";
import { pilotService } from "../services/pilotService.js";
import { stageService } from "../services/stageService.js";

const STATUS_LABELS = { open: "باز", submitted: "در انتظار بررسی", approved: "تأییدشده", needs_revision: "نیازمند اصلاح" };
const SECTIONS = Object.freeze([
  ["project", "پروژه"], ["floor", "طبقات"], ["plan", "Plan"], ["tour", "تور مجازی"],
]);
const DECISIONS = Object.freeze([
  ["proposal", "آماده دریافت پیشنهاد"], ["follow_up", "نیازمند پیگیری"],
  ["continue_pilot", "ادامه پایلوت"], ["stop", "توقف"], ["undecided", "هنوز تصمیم‌گیری نشده"],
]);
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
const select = (options, value = "") => {
  const node = control("select");
  options.forEach(([key, label]) => node.add(new Option(label, key)));
  node.value = value ?? "";
  return node;
};

export const StageSixteenPage = ({ pilotId }) => {
  const page = element("div", "stage-workspace");
  const permissions = sessionStore.getCurrentUser()?.permissions ?? [];
  const canRead = permissions.includes("pilots.read");
  const canManage = permissions.includes("customer_success.manage");
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
    if (!canRead) return renderError("برای مشاهده Stage 16 دسترسی لازم را ندارید.");
    page.replaceChildren(element("p", "loading-state", "در حال دریافت اطلاعات جلسه جمع‌بندی..."));
    try {
      const [pilot, f04, snapshots] = await Promise.all([
        pilotService.getPilotById(pilotId), experienceService.getF04(pilotId),
        stageService.getSnapshots(pilotId, 16),
      ]);
      const stage = pilot.stages.find(({ number }) => number === 16);
      if (!stage) return renderError("Stage 16 در ساختار این پرونده وجود ندارد.");
      if (stage.status === "locked" || pilot.currentStage < 16) {
        return renderError("Stage 16 تا تأیید Stage 15 و عبور از G5 قفل است.");
      }
      const editable = ["open", "needs_revision"].includes(stage.status);
      const feedback = element("p", "stage-actions__feedback", notice);
      const back = element("a", "back-link", "بازگشت به جزئیات پرونده");
      back.href = `#/pilots/${pilot.id}`;
      const header = element("header", "stage-workspace__header");
      const identity = element("div", "stage-workspace__identity");
      identity.append(
        element("span", "page-heading__eyebrow", `${pilot.code} — Stage 16 از ۱۹`),
        element("h1", "page-heading__title", "جلسه جمع‌بندی با مالک"),
        element("p", "draft-info", "هدف: تبدیل تجربه پایلوت به ارزش قابل بیان و نیاز قابل پیشنهاد."),
        element("p", "draft-info", "مسئول: موفقیت مشتری/فروش | زمان: پس از چند خروجی | مدت پیشنهادی: ۲۰ تا ۳۰ دقیقه"),
        element("p", "draft-info", "شرط عبور: ارزش دریافت‌شده، دامنه نیاز، تصمیم‌گیرنده و مانع خرید روشن باشد."),
      );
      header.append(identity, element("span", "status-badge stage-workspace__status", STATUS_LABELS[stage.status] ?? stage.status));
      page.replaceChildren(back, header, feedback);
      const form = element("section", "stage-form");
      const loginCount = control(); loginCount.type = "number"; loginCount.min = "0"; loginCount.value = f04?.main_platform_login_count ?? "";
      const viewedSections = new Map();
      const sectionList = document.createElement("fieldset"); sectionList.className = "checklist";
      sectionList.append(element("legend", "checklist__legend", "بخش‌های مشاهده‌شده در پلتفرم اصلی"));
      SECTIONS.forEach(([key, label]) => {
        const item = element("label", "checklist__item");
        const checkbox = document.createElement("input"); checkbox.type = "checkbox";
        checkbox.checked = (f04?.viewed_sections ?? []).includes(key);
        item.append(checkbox, element("span", "", label)); sectionList.append(item);
        viewedSections.set(key, { checkbox, item });
      });
      const reduction = select([["", "انتخاب نتیجه"], ["confirmed", "کاهش مراجعه/افزایش سرعت تأیید شد"], ["not_confirmed", "تأیید نشد"], ["unknown", "هنوز مشخص نیست"]], f04?.visit_reduction_result);
      const realizedValue = control("textarea"); realizedValue.rows = 3; realizedValue.value = f04?.realized_value ?? "";
      const customerNeed = control("textarea"); customerNeed.rows = 3; customerNeed.value = f04?.customer_need_summary ?? "";
      const projectCount = control(); projectCount.type = "number"; projectCount.min = "0"; projectCount.value = f04?.project_count ?? "";
      const userCount = control(); userCount.type = "number"; userCount.min = "0"; userCount.value = f04?.user_count ?? "";
      const frequency = control(); frequency.value = f04?.usage_frequency ?? "";
      const decisionMaker = control(); decisionMaker.value = f04?.decision_maker ?? "";
      const decision = select([["", "انتخاب نتیجه جلسه"], ...DECISIONS], f04?.closing_decision);
      const blocker = control("textarea"); blocker.rows = 3; blocker.value = f04?.purchase_blocker ?? "";
      const inputs = [loginCount, reduction, realizedValue, customerNeed, projectCount, userCount, frequency, decisionMaker, decision, blocker];
      inputs.forEach((input) => { input.disabled = !editable || !canManage; });
      viewedSections.forEach(({ checkbox }) => { checkbox.disabled = !editable || !canManage; });

      const grid = element("div", "stage-form__grid");
      grid.append(
        field("تعداد دفعات ورود", loginCount), field("کاهش مراجعه حضوری یا سرعت تصمیم‌گیری", reduction),
        field("ارزش واقعی ایجادشده برای مشتری", realizedValue), field("دامنه نیاز و افراد/پروژه‌های نیازمند دسترسی", customerNeed),
        field("تعداد پروژه‌ها", projectCount), field("تعداد کاربران", userCount),
        field("تناوب برداشت", frequency, "برای نمونه: هفتگی، ماهانه یا در نقاط عطف پروژه"),
        field("تصمیم‌گیرنده نهایی", decisionMaker), field("نتیجه جلسه", decision),
        field("فرایند تصمیم و مانع اصلی خرید", blocker),
      );
      form.append(element("h2", "stage-form__legend", "فرم F04 — جمع‌بندی تجاری"), grid, sectionList);

      const checklist = document.createElement("fieldset"); checklist.className = "checklist";
      checklist.append(element("legend", "checklist__legend", "کنترل جلسه مطابق راهنمای اجرایی"));
      const checks = [
        [() => loginCount.value !== "" && viewedSections.size && [...viewedSections.values()].some(({ checkbox }) => checkbox.checked), "تعداد دفعات ورود و بخش‌های مشاهده‌شده مشخص شد."],
        [() => Boolean(reduction.value), "کاهش مراجعه حضوری یا سرعت تصمیم‌گیری بررسی شد."],
        [() => customerNeed.value.trim().length >= 2, "افراد و پروژه‌های نیازمند دسترسی شناسایی شدند."],
        [() => Boolean(decision.value) && projectCount.value !== "" && frequency.value.trim().length >= 2, "تمایل به ادامه، تعداد پروژه‌ها و تناوب برداشت روشن شد."],
        [() => decisionMaker.value.trim().length >= 2 && blocker.value.trim().length >= 2, "تصمیم‌گیرنده، فرایند تصمیم و مانع اصلی خرید ثبت شد."],
      ].map(([test, label]) => {
        const item = element("label", "checklist__item"); const checkbox = document.createElement("input");
        checkbox.type = "checkbox"; checkbox.disabled = true; item.append(checkbox, element("span", "", label)); checklist.append(item);
        return { test, checkbox, item };
      });
      const refreshChecks = () => checks.forEach(({ test, checkbox }) => { checkbox.checked = Boolean(test()); });
      inputs.forEach((input) => { input.addEventListener("input", refreshChecks); input.addEventListener("change", refreshChecks); });
      viewedSections.forEach(({ checkbox }) => checkbox.addEventListener("change", refreshChecks)); refreshChecks();
      page.append(form, checklist);

      const validate = () => {
        const requiredText = [realizedValue, customerNeed, frequency, decisionMaker, blocker];
        requiredText.forEach((input) => input.setAttribute("aria-invalid", String(input.value.trim().length < 2)));
        [loginCount, projectCount, userCount].forEach((input) => input.setAttribute("aria-invalid", String(input.value === "" || Number(input.value) < 0)));
        [reduction, decision].forEach((input) => input.setAttribute("aria-invalid", String(!input.value)));
        const hasSection = [...viewedSections.values()].some(({ checkbox }) => checkbox.checked);
        viewedSections.forEach(({ item }) => item.classList.toggle("checklist__item--invalid", !hasSection));
        refreshChecks();
        return requiredText.every((input) => input.value.trim().length >= 2) &&
          [loginCount, projectCount, userCount].every((input) => input.value !== "" && Number(input.value) >= 0) &&
          Boolean(reduction.value && decision.value && hasSection);
      };
      const values = () => ({
        loginCount: loginCount.value, viewedSections: [...viewedSections].filter(([, v]) => v.checkbox.checked).map(([key]) => key),
        visitReductionResult: reduction.value, realizedValue: realizedValue.value.trim(), customerNeedSummary: customerNeed.value.trim(),
        projectCount: projectCount.value, userCount: userCount.value, usageFrequency: frequency.value.trim(),
        decisionMaker: decisionMaker.value.trim(), closingDecision: decision.value, purchaseBlocker: blocker.value.trim(),
      });
      if (editable && canManage) {
        const actions = element("div", "stage-actions");
        const save = element("button", "button button--ghost", "ذخیره جمع‌بندی");
        const submit = element("button", "button button--primary", "ارسال Stage 16 برای بررسی");
        save.type = submit.type = "button"; submit.hidden = !canSubmit;
        const persist = async () => { if (!validate()) return false; await experienceService.saveF04Closing(pilot.id, values()); return true; };
        save.addEventListener("click", async () => { save.disabled = true; try { if (await persist()) await load("جمع‌بندی جلسه در فرم F04 ذخیره شد."); else save.disabled = false; } catch (error) { feedback.textContent = error.message; save.disabled = false; } });
        submit.addEventListener("click", async () => { submit.disabled = true; try { if (!(await persist())) { submit.disabled = false; return; } await stageService.submit(pilot.id, 16); await load("Stage 16 برای بررسی ارسال شد."); } catch (error) { feedback.textContent = error.message; submit.disabled = false; } });
        actions.append(save, submit); page.append(actions);
      }
      if (stage.status === "submitted" && (canApprove || canReject)) {
        page.append(StageReviewPanel({
          pilotId: pilot.id, stageNumber: 16, title: "بررسی جلسه جمع‌بندی با مالک",
          approveLabel: "تأیید و ورود به Stage 17", approvedNotice: "Stage 16 تأیید و Stage 17 باز شد.",
          rejectedNotice: "Stage 16 برای اصلاح بازگردانده شد.", canApprove, canReject, reload: load,
          onApproved: async () => {
            const refreshedPilot = await pilotService.getPilotById(pilot.id);
            if (refreshedPilot.currentStage === 17) {
              window.location.hash = `#/pilots/${pilot.id}/stages/17`;
              return;
            }
            await load("Stage 16 تأیید شد، اما Stage 17 هنوز از سمت سرور فعال نشده است.");
          },
        }));
      }
      page.append(StageSnapshots({ snapshots, title: "نسخه‌های تأییدشده Stage 16" }));
    } catch (error) { renderError(error.message ?? "دریافت Stage 16 انجام نشد."); }
  };
  load(); return page;
};
