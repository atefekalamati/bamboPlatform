import { sessionStore } from "../app/sessionStore.js";
import { confirmDialog } from "../components/AppDialog.js";
import { Modal } from "../components/Modal.js";
import { INCIDENT_LABELS, RESPONSE_TARGETS, incidentSlaState } from "../features/incidents/incidentConstants.js";
import { formService } from "../services/formService.js";
import { incidentService } from "../services/incidentService.js";
import { userService } from "../services/userService.js";
import { formatPersianDateTime } from "../utils/dateFormatter.js";
import { formatIranDateTimeLocalValue, toBackendUtcDateTime } from "../utils/jalaliDateTime.js";

const node = (tag, className = "", text = "") => { const element = document.createElement(tag); element.className = className; element.textContent = text; return element; };
const info = (label, value) => { const item = node("div", "incident-info__item"); item.append(node("dt", "", label), node("dd", "", value || "ثبت نشده")); return item; };
const field = (labelText, key, value = "", rows = 3) => { const label = node("label", "form-field"); const input = document.createElement("textarea"); input.className = "form-field__input"; input.rows = rows; input.value = value ?? ""; input.dataset.key = key; label.append(node("span", "form-field__label", labelText), input); return { label, input }; };

const renderF05Preview = (documentData) => {
  const content = node("div", "incident-f05-preview");
  Object.entries(documentData.data).forEach(([sectionTitle, values]) => { const section = node("section", "incident-f05-preview__section"); section.append(node("h3", "", sectionTitle)); const list = node("dl", "incident-info"); Object.entries(values).forEach(([key, value]) => list.append(info(key, typeof value === "boolean" ? (value ? "بله" : "خیر") : Array.isArray(value) ? value.join("، ") : String(value ?? "")))); section.append(list); content.append(section); });
  return content;
};

export const IncidentDetailPage = ({ incidentId }) => {
  const permissions = sessionStore.getCurrentUser()?.permissions ?? [];
  const canRead = permissions.includes("incidents.read") && permissions.includes("pilots.read");
  const canManage = permissions.includes("incidents.manage");
  const page = node("div", "page incident-detail-page");
  if (!canRead) { page.append(node("p", "error-state__message", "برای مشاهده جزئیات رخداد دسترسی لازم را ندارید.")); return page; }
  const load = async () => {
    page.replaceChildren(node("p", "loading-state", "در حال دریافت جزئیات رخداد…"));
    try {
      const [incident, users] = await Promise.all([incidentService.getIncident(incidentId), userService.getUsers().catch(() => [])]);
      const userName = (id) => users.find((user) => user.id === id)?.displayName ?? (id ? `کاربر ${id}` : "ثبت نشده");
      const back = node("a", "back-link", "بازگشت به رخدادها"); back.href = "#/incidents";
      const header = node("header", `incident-detail__header severity-${incident.severity}`);
      const identity = node("div"); identity.append(node("span", "page-heading__eyebrow", incident.code), node("h1", "page-heading__title", INCIDENT_LABELS.type[incident.incidentType]));
      const badges = node("div", "incident-detail__badges"); badges.append(node("span", `incident-badge severity-${incident.severity}`, `شدت ${INCIDENT_LABELS.severity[incident.severity]}`), node("span", `incident-badge status-${incident.status}`, INCIDENT_LABELS.status[incident.status])); header.append(identity, badges);
      const cycle = node("section", "incident-cycle card"); cycle.append(node("h2", "section-title", "چرخه اقدام اصلاحی")); const steps = node("ol", "incident-cycle__steps");
      [["ثبت", true], ["مهار", Boolean(incident.containmentAction)], ["علت", Boolean(incident.rootCause)], ["اصلاح", incident.status === "closed"]].forEach(([label, done], index) => { const item = node("li", `incident-cycle__step${done ? " is-complete" : ""}`); item.append(node("span", "", String(index + 1)), node("strong", "", label), node("small", "", done ? "تکمیل‌شده" : "در انتظار")); steps.append(item); }); cycle.append(steps);
      const overview = node("section", "incident-overview card"); const overviewList = node("dl", "incident-info"); const sla = incidentSlaState(incident);
      overviewList.append(info("پرونده", String(incident.pilotId)), info("مأموریت", incident.missionId ? String(incident.missionId) : "بدون مأموریت"), info("مرحله", String(incident.stageNumber)), info("ثبت‌کننده", userName(incident.reportedByUserId)), info("مسئول فعلی", userName(incident.ownerUserId)), info("زمان وقوع", formatPersianDateTime(incident.occurredAt)), info("هدف واکنش", RESPONSE_TARGETS[incident.severity]), info("مهلت واکنش", formatPersianDateTime(incident.responseDueAt)), info("مهلت اصلاح", formatPersianDateTime(incident.correctionDueAt)), info("وضعیت SLA", sla.label)); overview.append(node("h2", "section-title", "مشخصات و SLA"), overviewList, node("p", "incident-description", incident.description));
      const actions = node("section", "incident-detail__actions card"); const f05 = node("button", "button button--ghost", "مشاهده فرم F05"); f05.type = "button";
      f05.hidden = !permissions.includes("forms.f05.read");
      f05.addEventListener("click", async () => { f05.disabled = true; try { const data = await formService.getPreview(`/pilots/${incident.pilotId}/forms/f05/${incident.id}`); Modal({ title: `فرم F05 — ${incident.code}`, content: renderF05Preview(data), triggerElement: f05, centered: true }); } finally { f05.disabled = false; } });
      const printF05 = node("button", "button button--ghost", "چاپ F05"); printF05.type = "button"; printF05.hidden = !permissions.includes("forms.print");
      printF05.addEventListener("click", async () => { const popup = window.open("", "_blank"); if (!popup) return; popup.document.write("<p dir='rtl'>در حال آماده‌سازی فرم…</p>"); try { const html = await formService.getPrintHtml(`/pilots/${incident.pilotId}/forms/f05/${incident.id}/print`); popup.document.open(); popup.document.write(html); popup.document.close(); window.setTimeout(() => popup.print(), 250); } catch { popup.close(); } });
      const pdfF05 = node("button", "button button--ghost", "دریافت PDF فرم F05"); pdfF05.type = "button"; pdfF05.hidden = !permissions.includes("forms.export_pdf");
      pdfF05.addEventListener("click", async () => { pdfF05.disabled = true; try { const file = await formService.downloadPdf(`/pilots/${incident.pilotId}/forms/f05/${incident.id}/pdf`); const url = URL.createObjectURL(file.blob); const link = document.createElement("a"); link.href = url; link.download = file.filename; link.click(); window.setTimeout(() => URL.revokeObjectURL(url), 1000); } finally { pdfF05.disabled = false; } });
      const stageLink = node("a", "button button--ghost", `مشاهده مرحله ${incident.stageNumber}`); stageLink.href = `#/pilots/${incident.pilotId}/stages/${incident.stageNumber}`; actions.append(f05, printF05, pdfF05, stageLink);
      if (canManage && incident.status !== "closed") {
        const editor = node("form", "incident-editor"); editor.append(node("h2", "section-title", "پیگیری و اقدام اصلاحی"));
        const containment = field("اقدام مهار", "containment_action", incident.containmentAction); const rootCause = field("علت ریشه‌ای", "root_cause", incident.rootCause); const corrective = field("اقدام اصلاحی", "corrective_action", incident.correctiveAction); const result = field("نتیجه", "result", incident.result); const evidence = field("شواهد", "evidence", incident.evidence); const lessons = field("درس‌آموخته", "lessons_learned", incident.lessonsLearned);
        const ownerLabel = node("label", "form-field"); const owner = document.createElement("select"); owner.className = "form-field__input"; owner.append(new Option("بدون مسئول", "")); users.filter((user) => user.isActive).forEach((user) => owner.append(new Option(user.displayName, String(user.id)))); owner.value = incident.ownerUserId ? String(incident.ownerUserId) : ""; ownerLabel.append(node("span", "form-field__label", "مسئول اقدام"), owner);
        const dueLabel = node("label", "form-field"); const due = document.createElement("input"); due.type = "datetime-local"; due.className = "form-field__input"; if (incident.correctionDueAt) due.value = formatIranDateTimeLocalValue(incident.correctionDueAt); dueLabel.append(node("span", "form-field__label", "موعد اقدام اصلاحی"), due);
        const statusLabel = node("label", "form-field"); const status = document.createElement("select"); status.className = "form-field__input"; [["open", "باز"], ["contained", "مهارشده"], ["resolved", "حل‌شده"]].forEach(([value, label]) => status.append(new Option(label, value))); status.value = incident.status; statusLabel.append(node("span", "form-field__label", "وضعیت"), status);
        const feedback = node("p", "form-feedback"); const save = node("button", "button button--primary", "ذخیره پیگیری"); save.type = "submit"; const close = node("button", "button button--danger", "بستن رخداد"); close.type = "button";
        editor.append(statusLabel, ownerLabel, dueLabel, containment.label, rootCause.label, corrective.label, result.label, evidence.label, lessons.label, feedback, save, close);
        const updatePayload = () => ({ status: status.value, owner_user_id: owner.value ? Number(owner.value) : null, correction_due_at: due.value ? toBackendUtcDateTime(due.value) : null, containment_action: containment.input.value || null, root_cause: rootCause.input.value || null, corrective_action: corrective.input.value || null, result: result.input.value || null, evidence: evidence.input.value || null, lessons_learned: lessons.input.value || null });
        editor.addEventListener("submit", async (event) => { event.preventDefault(); save.disabled = true; try { await incidentService.updateIncident(incident.id, updatePayload()); await load(); } catch (error) { feedback.textContent = error.status === 409 ? "اطلاعات رخداد هم‌زمان تغییر کرده است؛ صفحه دوباره دریافت شد." : error.message; feedback.dataset.type = "error"; if (error.status === 409) await load(); else save.disabled = false; } });
        close.addEventListener("click", async () => { const values = { rootCause: rootCause.input.value, correctiveAction: corrective.input.value, result: result.input.value, evidence: evidence.input.value, lessonsLearned: lessons.input.value }; if (!owner.value || !due.value) { feedback.textContent = "برای بستن رخداد، مسئول اقدام و موعد اصلاح را ثبت کنید."; feedback.dataset.type = "error"; return; } if (![values.rootCause, values.correctiveAction, values.result, values.lessonsLearned].every((value) => value.trim().length >= 2)) { feedback.textContent = "برای بستن رخداد، علت، اقدام اصلاحی، نتیجه و درس‌آموخته را کامل کنید."; feedback.dataset.type = "error"; return; } if (!(await confirmDialog({ title: incident.severity === "critical" ? "بستن رخداد بحرانی" : "بستن رخداد", message: "پس از بستن، رخداد قابل ویرایش نیست. اطلاعات نهایی تأیید می‌شود؟", confirmLabel: "تأیید و بستن", confirmClassName: "button button--danger", triggerElement: close }))) return; try { await incidentService.updateIncident(incident.id, updatePayload()); await incidentService.closeIncident(incident.id, values); await load(); } catch (error) { feedback.textContent = error.message; feedback.dataset.type = "error"; } });
        actions.append(editor);
      }
      const timeline = node("section", "incident-timeline card"); timeline.append(node("h2", "section-title", "زمان‌بندی ثبت‌شده")); const list = node("ol", "incident-timeline__list"); [["رخداد ثبت شد", incident.createdAt], ["آخرین تغییر", incident.updatedAt], ["رخداد بسته شد", incident.closedAt]].filter(([, value]) => value).forEach(([label, value]) => { const item = node("li"); item.append(node("strong", "", label), node("time", "", formatPersianDateTime(value))); list.append(item); }); timeline.append(list);
      page.replaceChildren(back, header, cycle, overview, actions, timeline);
    } catch (error) { const retry = node("button", "button button--primary", "تلاش مجدد"); retry.type = "button"; retry.addEventListener("click", load); page.replaceChildren(node("p", "error-state__message", error.message ?? "رخداد پیدا نشد."), retry); }
  };
  load(); return page;
};
