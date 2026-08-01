import { sessionStore } from "../app/sessionStore.js";
import { StageReviewPanel, StageSnapshots, stageElement as element } from "../components/StageShared.js";
import { commercialService } from "../services/commercialService.js";
import { pilotService } from "../services/pilotService.js";
import { stageService } from "../services/stageService.js";
import { userService } from "../services/userService.js";

const STATUS_LABELS = { open: "باز", submitted: "در انتظار بررسی", approved: "تأییدشده", needs_revision: "نیازمند اصلاح" };
const SLOTS = Object.freeze([
  ["day_0", "روز ارسال", 0, "توضیح پیشنهاد و تأیید دریافت", "نام تصمیم‌گیرنده و موعد بررسی"],
  ["day_2", "۲ روز بعد", 2, "پاسخ به ابهام‌ها", "فهرست سؤال/مانع"],
  ["day_5", "۵ روز بعد", 5, "بررسی نظر تصمیم‌گیرنده", "وضعیت تصمیم و اقدام بعدی"],
  ["day_7_10", "روز ۷ تا ۱۰", 7, "مذاکره شرایط همکاری", "توافق، اصلاح پیشنهاد یا علت توقف"],
]);
const control = (tag = "input") => { const node = document.createElement(tag); node.className = "stage-form__control"; return node; };
const field = (labelText, input, help = "") => {
  const label = element("label", "stage-form__field"); label.append(element("span", "stage-form__label", labelText), input);
  if (help) label.append(element("small", "draft-info", help)); return label;
};
const localDateTime = (date) => {
  const local = new Date(date.getTime() - date.getTimezoneOffset() * 60000);
  return local.toISOString().slice(0, 16);
};

export const StageEighteenPage = ({ pilotId }) => {
  const page = element("div", "stage-workspace");
  const currentUser = sessionStore.getCurrentUser();
  const permissions = currentUser?.permissions ?? [];
  const canRead = permissions.includes("pilots.read"); const canManage = permissions.includes("commercial.manage");
  const canSubmit = permissions.includes("checklists.manage"); const canApprove = permissions.includes("gate_approval.approve");
  const canReject = permissions.includes("gate_approval.reject");
  const renderError = (message) => {
    const state = element("div", "error-state"); const retry = element("button", "button button--primary", "تلاش مجدد");
    retry.type = "button"; retry.addEventListener("click", () => load());
    state.append(element("p", "error-state__message", message), retry); page.replaceChildren(state);
  };
  const load = async (notice = "") => {
    if (!canRead) return renderError("برای مشاهده Stage 18 دسترسی لازم را ندارید.");
    page.replaceChildren(element("p", "loading-state", "در حال دریافت برنامه پیگیری تجاری..."));
    try {
      const [pilot, proposal, followUps, users, snapshots] = await Promise.all([
        pilotService.getPilotById(pilotId), commercialService.getProposal(pilotId), commercialService.getFollowUps(pilotId),
        userService.getUsers().catch(() => currentUser ? [currentUser] : []), stageService.getSnapshots(pilotId, 18),
      ]);
      const stage = pilot.stages.find(({ number }) => number === 18);
      if (!stage) return renderError("Stage 18 در ساختار این پرونده وجود ندارد.");
      if (stage.status === "locked" || pilot.currentStage < 18) return renderError("Stage 18 تا تأیید Stage 17 قفل است.");
      if (!proposal) return renderError("پیشنهاد تجاری Stage 17 برای ساخت تقویم پیگیری پیدا نشد.");
      const editable = ["open", "needs_revision"].includes(stage.status); const feedback = element("p", "stage-actions__feedback", notice);
      const back = element("a", "back-link", "بازگشت به جزئیات پرونده"); back.href = `#/pilots/${pilot.id}`;
      const header = element("header", "stage-workspace__header"); const identity = element("div", "stage-workspace__identity");
      identity.append(
        element("span", "page-heading__eyebrow", `${pilot.code} — Stage 18 از ۱۹`),
        element("h1", "page-heading__title", "پیگیری تا تصمیم و عقد قرارداد"),
        element("p", "draft-info", "هدف: هر تماس برای رفع یک مانع مشخص انجام شود، نه صرفاً پرسش از تصمیم."),
        element("p", "draft-info", "مسئول: فروش | تقویم: روزهای ۰، ۲، ۵ و ۷ تا ۱۰ | ثبت: مانع، اقدام و تاریخ"),
        element("p", "draft-info", "شرط عبور: تصمیم روشن یا اقدام بعدی دارای مسئول و تاریخ قطعی ثبت شده باشد."),
      );
      header.append(identity, element("span", "status-badge stage-workspace__status", STATUS_LABELS[stage.status] ?? stage.status));
      page.replaceChildren(back, header, feedback);

      const currentBySlot = new Map(followUps.map((item) => [item.schedule_slot, item]));
      const activeUsers = users.filter(({ isActive }) => isActive); const controls = new Map(); const baseline = new Date(proposal.follow_up_at);
      SLOTS.forEach(([slot, title, offset, expectedAction, requiredOutput]) => {
        const current = currentBySlot.get(slot); const section = element("section", "stage-form"); const grid = element("div", "stage-form__grid");
        const obstacle = control("textarea"); obstacle.rows = 2; obstacle.value = current?.obstacle ?? "";
        const action = control("textarea"); action.rows = 2; action.value = current?.action ?? "";
        const owner = control("select"); owner.add(new Option("انتخاب مسئول", ""));
        activeUsers.forEach((user) => owner.add(new Option(`${user.displayName} — ${user.mobile}`, user.id))); owner.value = current?.owner_user_id ?? proposal.responsible_user_id ?? "";
        const dueAt = control(); dueAt.type = "datetime-local"; const suggested = new Date(baseline); suggested.setDate(suggested.getDate() + offset); dueAt.value = current?.due_at ? localDateTime(new Date(current.due_at)) : localDateTime(suggested);
        const result = control("textarea"); result.rows = 2; result.value = current?.result ?? "";
        const completedAt = control(); completedAt.type = "datetime-local"; completedAt.value = current?.completed_at ? localDateTime(new Date(current.completed_at)) : "";
        const inputs = [obstacle, action, owner, dueAt, result, completedAt]; inputs.forEach((input) => { input.disabled = !editable || !canManage; });
        grid.append(field("مانع مشخص", obstacle), field("اقدام انجام‌شده", action, `اقدام راهنما: ${expectedAction}`), field("مسئول اقدام", owner),
          field("موعد پیگیری", dueAt, slot === "day_7_10" ? "تاریخ باید بین روز هفتم تا دهم باشد." : "تاریخ بر اساس موعد ثبت‌شده پیشنهاد محاسبه شده است."),
          field("نتیجه", result, `خروجی اجباری: ${requiredOutput}`), field("زمان تکمیل", completedAt));
        section.append(element("h2", "stage-form__legend", title), grid); page.append(section);
        controls.set(slot, { obstacle, action, owner, dueAt, result, completedAt });
      });
      const validateSlot = ({ obstacle, action, owner, dueAt, result, completedAt }) => {
        [obstacle, action, result].forEach((input) => input.setAttribute("aria-invalid", String(input.value.trim().length < 2)));
        [owner, dueAt, completedAt].forEach((input) => input.setAttribute("aria-invalid", String(!input.value)));
        return obstacle.value.trim().length >= 2 && action.value.trim().length >= 2 && owner.value && dueAt.value && result.value.trim().length >= 2 && completedAt.value;
      };
      if (editable && canManage) {
        const actions = element("div", "stage-actions"); const save = element("button", "button button--ghost", "ذخیره برنامه پیگیری");
        const submit = element("button", "button button--primary", "ارسال Stage 18 برای بررسی"); save.type = submit.type = "button"; submit.hidden = !canSubmit;
        const persist = async () => {
          let valid = true; controls.forEach((group) => { valid = validateSlot(group) && valid; }); if (!valid) return false;
          for (const [slot, group] of controls) await commercialService.saveFollowUp(pilot.id, slot, {
            obstacle: group.obstacle.value.trim(), action: group.action.value.trim(), ownerUserId: group.owner.value,
            dueAt: group.dueAt.value, result: group.result.value.trim(), completedAt: group.completedAt.value,
          }); return true;
        };
        save.addEventListener("click", async () => { save.disabled = true; try { if (await persist()) await load("چهار پیگیری تجاری ذخیره شدند."); else save.disabled = false; } catch (error) { feedback.textContent = error.message; save.disabled = false; } });
        submit.addEventListener("click", async () => { submit.disabled = true; try { if (!(await persist())) { submit.disabled = false; return; } await stageService.submit(pilot.id, 18); await load("Stage 18 برای بررسی ارسال شد."); } catch (error) { feedback.textContent = error.message; submit.disabled = false; } });
        actions.append(save, submit); page.append(actions);
      }
      if (stage.status === "submitted" && (canApprove || canReject)) page.append(StageReviewPanel({
        pilotId: pilot.id, stageNumber: 18, title: "بررسی پیگیری‌های تجاری", approveLabel: "تأیید و ورود به Stage 19",
        approvedNotice: "Stage 18 تأیید و Stage 19 باز شد.", rejectedNotice: "Stage 18 برای اصلاح بازگردانده شد.", canApprove, canReject, reload: load,
      }));
      page.append(StageSnapshots({ snapshots, title: "نسخه‌های تأییدشده Stage 18" }));
    } catch (error) { renderError(error.message ?? "دریافت Stage 18 انجام نشد."); }
  };
  load(); return page;
};
