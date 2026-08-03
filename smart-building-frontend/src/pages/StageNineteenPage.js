import { sessionStore } from "../app/sessionStore.js";
import { StageReviewPanel, StageSnapshots, stageElement as element } from "../components/StageShared.js";
import { commercialService } from "../services/commercialService.js";
import { pilotService } from "../services/pilotService.js";
import { stageService } from "../services/stageService.js";
import { userService } from "../services/userService.js";

const STATUS_LABELS = { open: "باز", submitted: "در انتظار بررسی", approved: "تأییدشده", needs_revision: "نیازمند اصلاح" };
const OUTCOMES = Object.freeze([
  ["contract", "قرارداد منعقد شد"], ["ready_on_date", "آمادگی در تاریخ مشخص"],
  ["negotiation", "مذاکره با اقدام بعدی تاریخ‌دار"], ["rejected", "عدم پذیرش با دلیل"],
  ["closed", "خروج و بسته‌شدن پرونده"],
]);
const control = (tag = "input") => { const node = document.createElement(tag); node.className = "stage-form__control"; return node; };
const field = (labelText, input, help = "") => {
  const label = element("label", "stage-form__field"); label.append(element("span", "stage-form__label", labelText), input);
  if (help) label.append(element("small", "draft-info", help)); return label;
};
const localDateTime = (value) => {
  if (!value) return ""; const date = new Date(value); const local = new Date(date.getTime() - date.getTimezoneOffset() * 60000);
  return local.toISOString().slice(0, 16);
};

export const StageNineteenPage = ({ pilotId }) => {
  const page = element("div", "stage-workspace"); const currentUser = sessionStore.getCurrentUser();
  const permissions = currentUser?.permissions ?? [];
  const canRead = permissions.includes("pilots.read"); const canManage = permissions.includes("commercial.manage");
  const canSubmit = permissions.includes("checklists.manage"); const canApprove = permissions.includes("gate_approval.approve");
  const canReject = permissions.includes("gate_approval.reject"); const canApproveOutcome = canApprove;
  const renderError = (message) => {
    const state = element("div", "error-state"); const retry = element("button", "button button--primary", "تلاش مجدد");
    retry.type = "button"; retry.addEventListener("click", () => load()); state.append(element("p", "error-state__message", message), retry); page.replaceChildren(state);
  };
  const load = async (notice = "") => {
    if (!canRead) return renderError("برای مشاهده Stage 19 دسترسی لازم را ندارید.");
    page.replaceChildren(element("p", "loading-state", "در حال دریافت نتیجه نهایی پایلوت..."));
    try {
      const [pilot, outcomeData, users, snapshots] = await Promise.all([
        pilotService.getPilotById(pilotId), commercialService.getFinalOutcome(pilotId),
        userService.getUsers().catch(() => currentUser ? [currentUser] : []), stageService.getSnapshots(pilotId, 19),
      ]);
      const stage = pilot.stages.find(({ number }) => number === 19);
      if (!stage) return renderError("Stage 19 در ساختار این پرونده وجود ندارد.");
      if (stage.status === "locked" || pilot.currentStage < 19) return renderError("Stage 19 تا تأیید Stage 18 قفل است.");
      const editable = ["open", "needs_revision"].includes(stage.status); const feedback = element("p", "stage-actions__feedback", notice);
      const back = element("a", "back-link", "بازگشت به جزئیات پرونده"); back.href = `#/pilots/${pilot.id}`;
      const header = element("header", "stage-workspace__header"); const identity = element("div", "stage-workspace__identity");
      identity.append(
        element("span", "page-heading__eyebrow", `${pilot.code} — Stage 19 از ۱۹`),
        element("h1", "page-heading__title", "تبدیل پایلوت به قرارداد یا بستن پرونده"),
        element("p", "draft-info", "هدف: پایان رسمی، قابل اندازه‌گیری و قابل پیگیری پرونده."),
        element("p", "draft-info", "مسئول: فروش/مدیر پایلوت | زمان: پس از تصمیم قطعی | خروجی: نتیجه نهایی"),
        element("p", "draft-info", "شرط پایان: نتیجه، علت و اقدام بعدی نهایی ثبت و توسط مدیر پایلوت تأیید شود."),
      );
      header.append(identity, element("span", "status-badge stage-workspace__status", STATUS_LABELS[stage.status] ?? stage.status));
      page.replaceChildren(back, header, feedback);

      const form = element("section", "stage-form"); const grid = element("div", "stage-form__grid");
      const outcome = control("select"); outcome.add(new Option("انتخاب نتیجه نهایی", "")); OUTCOMES.forEach(([value, label]) => outcome.add(new Option(label, value))); outcome.value = outcomeData?.outcome ?? "";
      const reason = control("textarea"); reason.rows = 4; reason.value = outcomeData?.reason ?? "";
      const readyAt = control(); readyAt.type = "datetime-local"; readyAt.value = localDateTime(outcomeData?.ready_at);
      const successOwner = control("select"); successOwner.add(new Option("انتخاب مسئول موفقیت مشتری", ""));
      users.filter(({ isActive }) => isActive).forEach((user) => successOwner.add(new Option(`${user.displayName} — ${user.mobile}`, user.id))); successOwner.value = outcomeData?.success_owner_user_id ?? "";
      const periodic = control("select"); [["", "انتخاب وضعیت"], ["true", "برداشت دوره‌ای فعال است"], ["false", "برداشت دوره‌ای فعال نیست"]].forEach(([v, l]) => periodic.add(new Option(l, v)));
      periodic.value = outcomeData?.periodic_capture == null ? "" : String(outcomeData.periodic_capture);
      const userCount = control(); userCount.type = "number"; userCount.min = "1"; userCount.value = outcomeData?.contracted_user_count ?? "";
      const firstCapture = control(); firstCapture.type = "datetime-local"; firstCapture.value = localDateTime(outcomeData?.first_capture_at);
      const contractFields = [successOwner, periodic, userCount, firstCapture]; const inputs = [outcome, reason, readyAt, ...contractFields];
      inputs.forEach((input) => { input.disabled = !editable || !canManage || Boolean(outcomeData?.pilot_manager_approved); });
      grid.append(field("نتیجه نهایی", outcome), field("علت و اقدام بعدی", reason, "برای مذاکره، اقدام بعدی و تاریخ قطعی را در همین بخش ثبت کنید."),
        field("تاریخ آمادگی", readyAt), field("مسئول موفقیت مشتری", successOwner), field("برنامه برداشت دوره‌ای", periodic),
        field("تعداد کاربران نهایی", userCount), field("تاریخ اولین برداشت قراردادی", firstCapture));
      const approval = element("p", "draft-info", outcomeData?.pilot_manager_approved ? "نتیجه نهایی توسط مدیر پایلوت تأیید شده است." : "نتیجه نهایی هنوز تأیید مدیر پایلوت را ندارد.");
      form.append(element("h2", "stage-form__legend", "نتیجه نهایی پرونده"),
        element("p", "draft-info", "در صورت قرارداد، وضعیت مشتری، مسئول موفقیت، کاربران نهایی و اولین برداشت قراردادی تعیین می‌شوند."), grid, approval); page.append(form);

      const updateVisibility = () => {
        const isContract = outcome.value === "contract"; const needsReadyDate = outcome.value === "ready_on_date";
        contractFields.forEach((input) => { input.closest("label").hidden = !isContract; }); readyAt.closest("label").hidden = !needsReadyDate;
      }; outcome.addEventListener("change", updateVisibility); updateVisibility();
      const validate = () => {
        outcome.setAttribute("aria-invalid", String(!outcome.value));
        const reasonRequired = ["negotiation", "rejected", "closed"].includes(outcome.value); reason.setAttribute("aria-invalid", String(reasonRequired && reason.value.trim().length < 2));
        readyAt.setAttribute("aria-invalid", String(outcome.value === "ready_on_date" && !readyAt.value));
        const isContract = outcome.value === "contract"; successOwner.setAttribute("aria-invalid", String(isContract && !successOwner.value));
        periodic.setAttribute("aria-invalid", String(isContract && periodic.value === "")); userCount.setAttribute("aria-invalid", String(isContract && (!userCount.value || Number(userCount.value) <= 0)));
        firstCapture.setAttribute("aria-invalid", String(isContract && !firstCapture.value));
        return Boolean(outcome.value) && (!reasonRequired || reason.value.trim().length >= 2) && (outcome.value !== "ready_on_date" || readyAt.value) &&
          (!isContract || (successOwner.value && periodic.value !== "" && Number(userCount.value) > 0 && firstCapture.value));
      };
      const values = () => ({ outcome: outcome.value, reason: reason.value.trim(), readyAt: outcome.value === "ready_on_date" ? readyAt.value : "",
        successOwnerUserId: outcome.value === "contract" ? successOwner.value : "", periodicCapture: outcome.value === "contract" ? periodic.value === "true" : null,
        contractedUserCount: outcome.value === "contract" ? userCount.value : "", firstCaptureAt: outcome.value === "contract" ? firstCapture.value : "" });
      if (editable && canManage && !outcomeData?.pilot_manager_approved) {
        const save = element("button", "button button--ghost", "ذخیره نتیجه نهایی"); save.type = "button";
        save.addEventListener("click", async () => { if (!validate()) return; save.disabled = true; try { await commercialService.saveFinalOutcome(pilot.id, values()); await load("نتیجه نهایی ذخیره شد و در انتظار تأیید مدیر پایلوت است."); } catch (error) { feedback.textContent = error.message; save.disabled = false; } }); page.append(save);
      }
      if (editable && outcomeData && !outcomeData.pilot_manager_approved && canApproveOutcome) {
        const approveOutcome = element("button", "button button--primary", "تأیید نهایی مدیر پایلوت"); approveOutcome.type = "button";
        approveOutcome.addEventListener("click", async () => { approveOutcome.disabled = true; try { await commercialService.approveFinalOutcome(pilot.id); await load("نتیجه نهایی توسط مدیر پایلوت تأیید شد."); } catch (error) { feedback.textContent = error.message; approveOutcome.disabled = false; } }); page.append(approveOutcome);
      }
      if (editable && outcomeData?.pilot_manager_approved && canSubmit) {
        const submit = element("button", "button button--primary", "ارسال Stage 19 برای بررسی نهایی"); submit.type = "button";
        submit.addEventListener("click", async () => { submit.disabled = true; try { await stageService.submit(pilot.id, 19); await load("Stage 19 برای بررسی نهایی ارسال شد."); } catch (error) { feedback.textContent = error.message; submit.disabled = false; } }); page.append(submit);
      }
      if (stage.status === "submitted" && (canApprove || canReject)) page.append(StageReviewPanel({
        pilotId: pilot.id, stageNumber: 19, title: "بررسی نهایی و بستن پرونده", approveLabel: "تأیید نهایی پرونده",
        approvedNotice: "پرونده پایلوت با نتیجه ثبت‌شده نهایی شد.", rejectedNotice: "Stage 19 برای اصلاح بازگردانده شد.", canApprove, canReject, reload: load,
      }));
      page.append(StageSnapshots({ snapshots, title: "نسخه‌های نهایی Stage 19" }));
    } catch (error) { renderError(error.message ?? "دریافت Stage 19 انجام نشد."); }
  };
  load(); return page;
};
