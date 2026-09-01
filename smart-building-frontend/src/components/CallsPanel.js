import { Modal } from "./Modal.js";
import { callErrorMessage, callService, CALL_OUTCOMES, shouldPollCallStatus } from "../services/callService.js";
import { formatPersianDateTime } from "../utils/dateFormatter.js";

const node = (tag, className = "", text = "") => {
  const item = document.createElement(tag);
  item.className = className;
  item.textContent = text;
  return item;
};

const TECHNICAL_LABELS = Object.freeze({
  pending: "در انتظار", initiating: "در حال برقراری", ringing: "در حال زنگ‌خوردن",
  answered: "پاسخ داده شد", completed: "تکمیل شد", no_answer: "بدون پاسخ",
  busy: "مشغول", invalid_number: "شماره نامعتبر", failed: "ناموفق",
  cancelled: "لغوشده", retry_required: "نیازمند تلاش مجدد",
});
const OUTCOME_LABELS = Object.freeze({
  customer_confirmed: "تأیید مشتری", revision_requested: "درخواست اصلاح",
  callback_requested: "درخواست تماس مجدد", no_response: "بدون پاسخ تجاری",
  customer_rejected: "رد توسط مشتری", invalid_contact: "اطلاعات تماس نامعتبر",
  escalated_to_manager: "ارجاع به مدیر", contract_follow_up: "پیگیری قرارداد",
  follow_up_completed: "پیگیری تکمیل شد",
});
const RETRY_STATUSES = new Set(["no_answer", "busy", "failed", "retry_required"]);
const OUTCOME_STATUSES = new Set(["answered", "completed", "no_answer", "busy", "failed"]);
const NEXT_ACTION_OUTCOMES = new Set(["callback_requested", "revision_requested", "contract_follow_up"]);
const POLL_INTERVAL_MS = 8_000;
const MAX_POLL_ATTEMPTS = 15;

const field = (labelText, control, help = "") => {
  const label = node("label", "stage-form__field");
  label.append(node("span", "stage-form__label", labelText), control);
  if (help) label.append(node("small", "draft-info", help));
  return label;
};

const modalForm = () => node("form", "stage-form calls-modal-form");

export const CallsPanel = ({ pilotId, stageNumber, permissions = [], required = false }) => {
  const section = node("section", "stage-form calls-panel");
  const heading = node("div", "calls-panel__heading");
  const titleArea = node("div");
  titleArea.append(
    node("h2", "stage-form__legend", "تماس‌های این مرحله"),
    node("p", "draft-info", required
      ? "برای عبور از این مرحله، نتیجه تماس معتبر باید در بک‌اند ثبت شود."
      : "ثبت تماس در این مرحله اختیاری است."),
  );
  const actions = node("div", "calls-panel__actions");
  const list = node("div", "calls-list");
  const feedback = node("p", "stage-actions__feedback");
  list.setAttribute("aria-live", "polite");
  feedback.setAttribute("aria-live", "polite");
  const canRead = permissions.includes("calls.read");
  const canInitiate = permissions.includes("calls.initiate");
  const canRecord = permissions.includes("calls.record_outcome");
  const canRetry = permissions.includes("calls.retry");
  const canOverride = permissions.includes("calls.override");
  const canReadRecording = permissions.includes("calls.recording.read");
  let listController = null;
  let pollTimer = null;
  let pollAttempts = 0;
  let latestCalls = [];
  let initiateButton = null;

  const showError = (error, localFeedback = feedback) => { localFeedback.textContent = callErrorMessage(error); };

  const openInitiate = (trigger) => {
    const form = modalForm();
    const confirmation = node("div", "calls-confirmation");
    const lastDestination = latestCalls[0]?.destinationMasked;
    confirmation.append(
      node("p", "", lastDestination ? `مخاطب پرونده: ${lastDestination}` : "شماره مالک از اطلاعات معتبر پرونده توسط بک‌اند انتخاب می‌شود."),
      node("p", "draft-info", `مرحله مرتبط: ${stageNumber} — تماس فقط از طریق سرویس بک‌اند بامبو برقرار می‌شود.`),
    );
    const purpose = document.createElement("input"); purpose.className = "stage-form__control";
    purpose.value = stageNumber === 18 ? "پیگیری تجاری" : "هماهنگی با مشتری";
    const consent = document.createElement("input"); consent.type = "checkbox";
    const consentLabel = node("label", "calls-consent"); consentLabel.append(consent, node("span", "", "رضایت مشتری برای ضبط تماس ثبت شده است"));
    const footer = node("div", "modal__actions");
    const cancel = node("button", "button button--ghost", "لغو"); cancel.type = "button";
    const submit = node("button", "button button--primary", "آغاز تماس"); submit.type = "submit";
    const modalFeedback = node("p", "form-field__error"); modalFeedback.setAttribute("aria-live", "assertive");
    footer.append(cancel, submit); form.append(confirmation, field("هدف تماس", purpose), consentLabel, modalFeedback, footer);
    let modal;
    cancel.addEventListener("click", () => modal.close());
    form.addEventListener("submit", async (event) => {
      event.preventDefault(); submit.disabled = true;
      try {
        await callService.initiate(pilotId, stageNumber, { purpose: purpose.value, recordingConsent: consent.checked });
        modal.close(); await load("درخواست تماس ثبت شد.");
      } catch (error) { showError(error, modalFeedback); submit.disabled = false; }
    });
    modal = Modal({ title: "تأیید شروع تماس", content: form, triggerElement: trigger, centered: true });
  };

  const openOutcome = (call, trigger) => {
    const form = modalForm();
    const outcome = document.createElement("select"); outcome.className = "stage-form__control";
    outcome.append(new Option("انتخاب نتیجه", ""));
    CALL_OUTCOMES.forEach((value) => outcome.append(new Option(OUTCOME_LABELS[value], value)));
    const summary = document.createElement("textarea"); summary.className = "stage-form__control"; summary.rows = 4; summary.value = call.summary ?? "";
    const nextAction = document.createElement("textarea"); nextAction.className = "stage-form__control"; nextAction.rows = 2; nextAction.value = call.nextAction ?? "";
    const callbackAt = document.createElement("input"); callbackAt.className = "stage-form__control"; callbackAt.type = "datetime-local";
    const callbackField = field("زمان تماس مجدد", callbackAt, "در صورت انتخاب درخواست تماس مجدد الزامی است.");
    const updateConditionalFields = () => {
      const needsAction = NEXT_ACTION_OUTCOMES.has(outcome.value);
      nextAction.required = needsAction;
      callbackAt.required = outcome.value === "callback_requested";
      callbackField.hidden = outcome.value !== "callback_requested";
    };
    outcome.addEventListener("change", updateConditionalFields); updateConditionalFields();
    const footer = node("div", "modal__actions");
    const cancel = node("button", "button button--ghost", "لغو"); cancel.type = "button";
    const submit = node("button", "button button--primary", "ثبت نتیجه تماس"); submit.type = "submit";
    const modalFeedback = node("p", "form-field__error"); modalFeedback.setAttribute("aria-live", "assertive");
    footer.append(cancel, submit);
    form.append(field("نتیجه تماس", outcome), field("خلاصه تماس", summary), field("اقدام بعدی", nextAction), callbackField, modalFeedback, footer);
    let modal;
    cancel.addEventListener("click", () => modal.close());
    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      const invalid = !outcome.value || summary.value.trim().length < 3
        || (nextAction.required && !nextAction.value.trim()) || (callbackAt.required && !callbackAt.value);
      outcome.setAttribute("aria-invalid", String(!outcome.value));
      summary.setAttribute("aria-invalid", String(summary.value.trim().length < 3));
      nextAction.setAttribute("aria-invalid", String(nextAction.required && !nextAction.value.trim()));
      callbackAt.setAttribute("aria-invalid", String(callbackAt.required && !callbackAt.value));
      if (invalid) return;
      submit.disabled = true;
      try {
        await callService.recordOutcome(call.id, { outcome: outcome.value, summary: summary.value, nextAction: nextAction.value, callbackAt: callbackAt.value });
        modal.close(); await load("نتیجه تماس ثبت شد.");
      } catch (error) { showError(error, modalFeedback); submit.disabled = false; }
    });
    modal = Modal({ title: "ثبت نتیجه تماس", content: form, triggerElement: trigger, centered: true });
  };

  const openOverride = (call, trigger) => {
    const form = modalForm();
    const reason = document.createElement("textarea"); reason.className = "stage-form__control"; reason.rows = 4;
    const footer = node("div", "modal__actions");
    const cancel = node("button", "button button--ghost", "لغو"); cancel.type = "button";
    const submit = node("button", "button button--danger", "ثبت Override"); submit.type = "submit";
    const modalFeedback = node("p", "form-field__error"); modalFeedback.setAttribute("aria-live", "assertive");
    footer.append(cancel, submit); form.append(field("دلیل مدیریتی", reason, "حداقل ۱۰ نویسه؛ این عملیات در Audit ثبت می‌شود."), modalFeedback, footer);
    let modal;
    cancel.addEventListener("click", () => modal.close());
    form.addEventListener("submit", async (event) => {
      event.preventDefault(); const invalid = reason.value.trim().length < 10;
      reason.setAttribute("aria-invalid", String(invalid)); if (invalid) return;
      submit.disabled = true;
      try { await callService.override(call.id, reason.value); modal.close(); await load("Override مدیریتی ثبت شد."); }
      catch (error) { showError(error, modalFeedback); submit.disabled = false; }
    });
    modal = Modal({ title: "عبور مدیریتی از الزام تماس", content: form, triggerElement: trigger, centered: true });
  };

  const renderCall = (call) => {
    const card = node("article", "calls-card");
    const header = node("header", "calls-card__header");
    header.append(
      node("strong", "", call.destinationMasked || "شماره ثبت نشده"),
      node("span", "status-badge", TECHNICAL_LABELS[call.technicalStatus] ?? "وضعیت نامشخص"),
    );
    const details = node("dl", "calls-card__details");
    [
      ["زمان درخواست", formatPersianDateTime(call.requestedAt)],
      ["نتیجه", call.businessOutcome ? OUTCOME_LABELS[call.businessOutcome] ?? "نتیجه نامشخص" : "ثبت نشده"],
      ["خلاصه", call.summary || "ثبت نشده"],
      ["تعداد تلاش", String(call.attempts.length)],
      ["مدت تماس", Number.isFinite(call.durationSeconds) ? `${call.durationSeconds} ثانیه` : "ثبت نشده"],
      ["تماس مجدد", call.callbackAt ? formatPersianDateTime(call.callbackAt) : "ثبت نشده"],
    ].forEach(([label, value]) => { details.append(node("dt", "", label), node("dd", "", value)); });
    const cardActions = node("div", "calls-card__actions");
    if (canRecord && OUTCOME_STATUSES.has(call.technicalStatus)) {
      const button = node("button", "button button--ghost", "ثبت نتیجه"); button.type = "button"; button.onclick = () => openOutcome(call, button); cardActions.append(button);
    }
    if (canRetry && RETRY_STATUSES.has(call.technicalStatus)) {
      const button = node("button", "button button--ghost", "تلاش مجدد"); button.type = "button";
      button.onclick = async () => { button.disabled = true; try { await callService.retry(call.id); await load("تلاش مجدد تماس ثبت شد."); } catch (error) { showError(error); button.disabled = false; } };
      cardActions.append(button);
    }
    if (canOverride && !call.overriddenAt) {
      const button = node("button", "button button--ghost", "Override مدیریتی"); button.type = "button"; button.onclick = () => openOverride(call, button); cardActions.append(button);
    }
    if (canReadRecording && call.recordingConsent) {
      const button = node("button", "button button--ghost", "مرجع ضبط"); button.type = "button";
      button.onclick = async () => { button.disabled = true; try { const result = await callService.getRecordingReference(call.id); feedback.textContent = `مرجع ضبط: ${result.reference}`; } catch (error) { showError(error); } finally { button.disabled = false; } };
      cardActions.append(button);
    }
    card.append(header, details, cardActions); return card;
  };

  const stopPolling = () => { window.clearTimeout(pollTimer); pollTimer = null; };
  const schedulePolling = (calls) => {
    stopPolling();
    if (!shouldPollCallStatus(calls) || pollAttempts >= MAX_POLL_ATTEMPTS) {
      if (pollAttempts >= MAX_POLL_ATTEMPTS && shouldPollCallStatus(calls)) feedback.textContent = "وضعیت نهایی تماس هنوز از سرور دریافت نشده است؛ برای بررسی دوباره از دکمه به‌روزرسانی استفاده کنید.";
      return;
    }
    pollTimer = window.setTimeout(async () => {
      if (!section.isConnected) { listController?.abort(); stopPolling(); return; }
      if (document.visibilityState === "hidden") { schedulePolling(calls); return; }
      pollAttempts += 1; await load("", false);
    }, POLL_INTERVAL_MS);
  };

  const load = async (notice = "", resetPolling = true) => {
    if (resetPolling) pollAttempts = 0;
    listController?.abort(); listController = new AbortController();
    feedback.textContent = notice; list.replaceChildren(node("p", "loading-state", "در حال دریافت تماس‌ها..."));
    try {
      const calls = await callService.list(pilotId, stageNumber, { signal: listController.signal });
      latestCalls = calls;
      const hasOpenCall = shouldPollCallStatus(calls);
      if (initiateButton) { initiateButton.disabled = hasOpenCall; initiateButton.title = hasOpenCall ? "تا تعیین وضعیت تماس جاری، تماس جدید قابل آغاز نیست." : ""; }
      list.replaceChildren(...(calls.length ? calls.map(renderCall) : [node("p", "empty-state", "هنوز تماسی برای این مرحله ثبت نشده است.")]));
      schedulePolling(calls);
    } catch (error) {
      if (error?.name === "AbortError") return;
      stopPolling(); list.replaceChildren(node("p", "error-state__message", callErrorMessage(error)));
    }
  };

  if (canInitiate) {
    initiateButton = node("button", "button button--primary", "آغاز تماس"); initiateButton.type = "button";
    initiateButton.addEventListener("click", () => openInitiate(initiateButton)); actions.append(initiateButton);
  }
  if (canRead) {
    const refresh = node("button", "button button--ghost", "به‌روزرسانی وضعیت تماس‌ها");
    refresh.type = "button";
    refresh.addEventListener("click", async () => {
      refresh.disabled = true;
      try { await load("آخرین وضعیت تماس‌ها از سرور دریافت شد."); }
      finally { refresh.disabled = false; }
    });
    actions.append(refresh);
  }
  heading.append(titleArea, actions); section.append(heading, feedback, list);
  if (canRead) load(); else list.append(node("p", "error-state__message", "دسترسی مشاهده تماس‌ها را ندارید."));
  return section;
};
