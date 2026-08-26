import { request } from "./httpClient.js";
import { toBackendUtcDateTime } from "../utils/jalaliDateTime.js";

const mapIncident = (item) => ({
  id: item.id, pilotId: item.pilot_id, missionId: item.mission_id, sequence: item.sequence,
  code: item.code, occurredAt: item.occurred_at, reportedByUserId: item.reported_by_user_id,
  stageNumber: item.stage_number, severity: item.severity, incidentType: item.incident_type,
  description: item.description, containmentAction: item.containment_action,
  notifiedPeople: item.notified_people ?? [], rootCause: item.root_cause,
  correctiveAction: item.corrective_action, ownerUserId: item.owner_user_id,
  responseDueAt: item.response_due_at, correctionDueAt: item.correction_due_at,
  result: item.result, evidence: item.evidence, lessonsLearned: item.lessons_learned,
  status: item.status, closedByUserId: item.closed_by_user_id, closedAt: item.closed_at,
  createdAt: item.created_at, updatedAt: item.updated_at,
  pilotCode: item.pilot_code ?? null,
  pilotName: item.pilot_display_name ?? null,
  slaDueAt: item.sla_due_at ?? item.response_due_at,
});

const appendQuery = (values) => {
  const query = new URLSearchParams();
  Object.entries(values).forEach(([key, value]) => {
    if (value !== "" && value !== null && value !== undefined) query.set(key, String(value));
  });
  return query.toString();
};

export const mapGlobalIncidentListResponse = (response) => {
  if (!response || !Array.isArray(response.items) || !response.summary) {
    throw new TypeError("پاسخ فهرست سراسری رخدادها با قرارداد بک‌اند مطابقت ندارد.");
  }
  return {
    items: response.items.map(mapIncident),
    page: Number(response.page),
    pageSize: Number(response.page_size),
    total: Number(response.total),
    totalPages: Number(response.total_pages),
    summary: response.summary,
  };
};

export const mapIncidentListResponse = (response) => {
  if (Array.isArray(response)) return response.map(mapIncident);
  if (!response || !Array.isArray(response.items)) {
    throw new TypeError("پاسخ فهرست رخدادها با قرارداد بک‌اند مطابقت ندارد.");
  }
  return response.items.map(mapIncident);
};

const createPayload = (values) => ({
  mission_id: values.missionId ? Number(values.missionId) : null,
  occurred_at: toBackendUtcDateTime(values.occurredAt),
  stage_number: Number(values.stageNumber), severity: values.severity,
  incident_type: values.incidentType, description: values.description.trim(),
  containment_action: values.containmentAction?.trim() || null,
  notified_people: values.notifiedPeople ?? [],
  owner_user_id: values.ownerUserId ? Number(values.ownerUserId) : null,
  correction_due_at: values.correctionDueAt ? toBackendUtcDateTime(values.correctionDueAt) : null,
});

export const incidentService = Object.freeze({
  getIncidents: async (filters = {}, { signal } = {}) => mapGlobalIncidentListResponse(
    await request(`/incidents?${appendQuery(filters)}`, { signal }),
  ),
  getPilotIncidents: async (pilotId) => mapIncidentListResponse(
    await request(`/pilots/${pilotId}/incidents?page=1&page_size=200`),
  ),
  createIncident: async (pilotId, values) => mapIncident(await request(`/pilots/${pilotId}/incidents`, { method: "POST", body: JSON.stringify(createPayload(values)) })),
  getIncident: async (incidentId) => mapIncident(await request(`/incidents/${incidentId}`)),
  updateIncident: async (incidentId, values) => mapIncident(await request(`/incidents/${incidentId}`, { method: "PATCH", body: JSON.stringify(values) })),
  closeIncident: async (incidentId, values) => mapIncident(await request(`/incidents/${incidentId}/close`, { method: "POST", body: JSON.stringify({ root_cause: values.rootCause.trim(), corrective_action: values.correctiveAction.trim(), result: values.result.trim(), evidence: values.evidence?.trim() || null, lessons_learned: values.lessonsLearned.trim(), confirmed: true }) })),
});
