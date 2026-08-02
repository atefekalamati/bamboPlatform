import { sessionStore } from "../app/sessionStore.js";
import { INCIDENT_LABELS } from "../features/incidents/incidentConstants.js";
import { incidentService } from "../services/incidentService.js";

const node = (tag, className = "", text = "") => { const element = document.createElement(tag); element.className = className; element.textContent = text; return element; };

export const PilotIncidentsPanel = ({ pilotId }) => {
  const permissions = sessionStore.getCurrentUser()?.permissions ?? [];
  const panel = node("section", "pilot-incidents card");
  const header = node("header", "pilot-incidents__header"); header.append(node("h2", "section-title", "رخدادهای پرونده"));
  if (permissions.includes("incidents.manage")) { const create = node("a", "button button--primary", "ثبت رخداد"); create.href = `#/pilots/${pilotId}/incidents/new`; header.append(create); }
  const content = node("div", "pilot-incidents__content"); panel.append(header, content);
  const load = async () => { content.replaceChildren(node("p", "loading-state", "در حال دریافت رخدادها…")); try { const incidents = await incidentService.getPilotIncidents(pilotId); if (!incidents.length) { content.replaceChildren(node("p", "notification-empty", "هیچ رخدادی برای این پایلوت ثبت نشده است.")); return; } const list = node("div", "pilot-incidents__list"); incidents.slice(0, 6).forEach((incident) => { const link = node("a", `pilot-incident severity-${incident.severity}`); link.href = `#/incidents/${incident.id}`; link.append(node("strong", "", incident.code), node("span", "", `${INCIDENT_LABELS.severity[incident.severity]} · ${INCIDENT_LABELS.status[incident.status]} · مرحله ${incident.stageNumber}`), node("p", "", incident.description)); list.append(link); }); const all = node("a", "button-link", "مشاهده همه رخدادها"); all.href = "#/incidents"; content.replaceChildren(list, all); } catch (error) { content.replaceChildren(node("p", "error-state__message", error.message ?? "دریافت رخدادها انجام نشد.")); } };
  load(); return panel;
};
