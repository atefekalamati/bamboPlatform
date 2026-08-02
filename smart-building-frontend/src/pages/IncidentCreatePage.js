import { sessionStore } from "../app/sessionStore.js";
import { confirmDialog } from "../components/AppDialog.js";
import { IncidentForm } from "../components/IncidentForm.js";
import { incidentService } from "../services/incidentService.js";
import { missionService } from "../services/missionService.js";
import { pilotService } from "../services/pilotService.js";
import { userService } from "../services/userService.js";

const node = (tag, className = "", text = "") => { const element = document.createElement(tag); element.className = className; element.textContent = text; return element; };

export const IncidentCreatePage = ({ pilotId }) => {
  const permissions = sessionStore.getCurrentUser()?.permissions ?? [];
  const page = node("div", "page incident-create-page");
  if (!permissions.includes("incidents.manage")) { page.append(node("p", "error-state__message", "برای ثبت رخداد دسترسی لازم را ندارید.")); return page; }
  const heading = node("header", "page-heading"); heading.append(node("a", "back-link", "بازگشت به رخدادها"), node("h1", "page-heading__title", "ثبت رخداد جدید"), node("p", "page-heading__description", "کد رخداد و مهلت واکنش توسط backend ایجاد می‌شود.")); heading.querySelector("a").href = "#/incidents";
  const content = node("section", "incident-form-shell card"); page.append(heading, content);
  const load = async () => {
    content.replaceChildren(node("p", "loading-state", "در حال آماده‌سازی فرم…"));
    try {
      const [pilot, missions, users] = await Promise.all([pilotService.getPilotById(pilotId), missionService.getMissions(pilotId).catch(() => []), userService.getUsers().catch(() => [])]);
      content.replaceChildren(IncidentForm({ pilot, missions, users, onCancel: () => { window.location.hash = "#/incidents"; }, onSubmit: async (values) => {
        if (values.severity === "critical" && !(await confirmDialog({ title: "ثبت رخداد بحرانی", message: "این رخداد می‌تواند مراحل بعدی پایلوت را نامعتبر کند و اعلان فوری برای مسئول بفرستد. ثبت شود؟", confirmLabel: "ثبت رخداد بحرانی" }))) return;
        const created = await incidentService.createIncident(pilotId, values); window.location.hash = `#/incidents/${created.id}`;
      } }));
    } catch (error) { const retry = node("button", "button button--primary", "تلاش مجدد"); retry.type = "button"; retry.addEventListener("click", load); content.replaceChildren(node("p", "error-state__message", error.message ?? "فرم رخداد آماده نشد."), retry); }
  };
  load(); return page;
};
