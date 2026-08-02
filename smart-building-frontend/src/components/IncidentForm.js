import { INCIDENT_LABELS } from "../features/incidents/incidentConstants.js";

const node = (tag, className = "", text = "") => { const element = document.createElement(tag); element.className = className; element.textContent = text; return element; };
const field = (labelText, control, required = false) => {
  const label = node("label", "form-field");
  const text = node("span", "form-field__label", `${labelText}${required ? " *" : ""}`);
  control.classList.add("form-field__input"); control.required = required;
  label.append(text, control); return label;
};
const options = (values, placeholder = null) => {
  const select = document.createElement("select");
  if (placeholder) select.append(new Option(placeholder, ""));
  values.forEach(([value, label]) => select.append(new Option(label, value)));
  return select;
};

export const IncidentForm = ({ pilot, missions = [], users = [], initialStage = null, onSubmit, onCancel }) => {
  const form = node("form", "incident-form");
  const grid = node("div", "incident-form__grid");
  const pilotValue = document.createElement("input"); pilotValue.value = `${pilot.code} — ${pilot.displayName}`; pilotValue.disabled = true;
  const mission = options(missions.map((item) => [String(item.id), item.code]), "بدون مأموریت");
  const stage = document.createElement("input"); stage.type = "number"; stage.min = "1"; stage.max = "19"; stage.value = initialStage ?? Math.min(pilot.currentStage, 19);
  const occurredAt = document.createElement("input"); occurredAt.type = "datetime-local"; occurredAt.value = new Date(Date.now() - new Date().getTimezoneOffset() * 60000).toISOString().slice(0, 16);
  const severity = options(Object.entries(INCIDENT_LABELS.severity)); severity.value = "normal";
  const incidentType = options(Object.entries(INCIDENT_LABELS.type));
  const owner = options(users.filter((user) => user.isActive).map((user) => [String(user.id), user.displayName]), "بدون مسئول");
  const correctionDueAt = document.createElement("input"); correctionDueAt.type = "datetime-local";
  const description = document.createElement("textarea"); description.rows = 4; description.maxLength = 10000;
  const containment = document.createElement("textarea"); containment.rows = 3; containment.maxLength = 10000;
  const notified = document.createElement("input"); notified.placeholder = "نام افراد را با ویرگول جدا کنید";
  const banner = node("div", "incident-critical-banner"); banner.hidden = true; banner.setAttribute("role", "alert"); banner.textContent = "هشدار: رخداد بحرانی می‌تواند مراحل بعد از مرحله ۱۳ را مسدود کند و برای مسئول رخداد اعلان فوری می‌فرستد.";
  severity.addEventListener("change", () => { banner.hidden = severity.value !== "critical"; containment.required = severity.value === "critical"; });
  grid.append(field("پرونده", pilotValue), field("مأموریت مرتبط", mission), field("شماره مرحله", stage, true), field("زمان وقوع", occurredAt, true), field("شدت رخداد", severity, true), field("نوع رخداد", incidentType, true), field("مسئول پیگیری", owner), field("موعد اقدام اصلاحی", correctionDueAt));
  const descriptionField = field("شرح دقیق رخداد", description, true); descriptionField.classList.add("incident-form__wide");
  const containmentField = field("اقدام فوری برای مهار", containment); containmentField.classList.add("incident-form__wide");
  const notifiedField = field("افراد یا واحدهای مطلع‌شده", notified); notifiedField.classList.add("incident-form__wide");
  grid.append(descriptionField, containmentField, notifiedField);
  const error = node("p", "form-feedback"); const actions = node("div", "incident-form__actions");
  const submit = node("button", "button button--primary", "ثبت رخداد"); submit.type = "submit";
  const cancel = node("button", "button button--ghost", "لغو"); cancel.type = "button"; cancel.addEventListener("click", onCancel);
  actions.append(submit, cancel); form.append(banner, grid, error, actions);
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    if (Number(stage.value) > pilot.currentStage) { error.textContent = "رخداد را نمی‌توان برای مرحله‌ای ثبت کرد که هنوز شروع نشده است."; error.dataset.type = "error"; return; }
    if (severity.value === "critical" && !containment.value.trim()) { error.textContent = "برای رخداد بحرانی، اقدام فوری مهار را ثبت کنید."; error.dataset.type = "error"; containment.focus(); return; }
    submit.disabled = true; submit.textContent = "در حال ثبت…";
    try { await onSubmit({ missionId: mission.value, stageNumber: stage.value, occurredAt: occurredAt.value, severity: severity.value, incidentType: incidentType.value, description: description.value, containmentAction: containment.value, notifiedPeople: notified.value.split("،").join(",").split(",").map((value) => value.trim()).filter(Boolean), ownerUserId: owner.value, correctionDueAt: correctionDueAt.value }); }
    catch (exception) { error.textContent = exception.message ?? "ثبت رخداد انجام نشد."; error.dataset.type = "error"; submit.disabled = false; submit.textContent = "ثبت رخداد"; }
  });
  return form;
};
