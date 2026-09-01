import assert from "node:assert/strict";
import test from "node:test";
import { mapGlobalIncidentListResponse, mapIncidentListResponse } from "../src/services/incidentService.js";

const backendIncident = {
  id: 7,
  pilot_id: 2,
  mission_id: null,
  sequence: 1,
  code: "INC-0001",
  occurred_at: "2026-08-02T10:00:00",
  reported_by_user_id: 1,
  stage_number: 8,
  severity: "critical",
  incident_type: "process",
  description: "نمونه رخداد",
  notified_people: [],
  response_due_at: "2026-08-02T10:30:00",
  status: "open",
  created_at: "2026-08-02T10:00:00",
  updated_at: "2026-08-02T10:00:00",
};

test("maps the paginated incident list contract returned by backend", () => {
  const incidents = mapIncidentListResponse({
    items: [backendIncident], total: 1, page: 1, page_size: 20, total_pages: 1,
    summary: { open: 1, contained: 0, resolved: 0, closed: 0, critical: 1, overdue: 0 },
  });
  assert.equal(incidents.length, 1);
  assert.equal(incidents[0].pilotId, 2);
  assert.equal(incidents[0].incidentType, "process");
});

test("fails clearly when the backend list contract is invalid", () => {
  assert.throws(() => mapIncidentListResponse({ items: null }), /قرارداد بک‌اند/);
});

test("keeps compatibility with the former array response", () => {
  assert.equal(mapIncidentListResponse([backendIncident])[0].code, "INC-0001");
});

test("maps the scoped global incident contract and its server summary", () => {
  const response = mapGlobalIncidentListResponse({
    items: [{ ...backendIncident, pilot_code: "PIL-1405-001", pilot_display_name: "پرونده تست", sla_due_at: backendIncident.response_due_at }],
    page: 2, page_size: 20, total: 25, total_pages: 2,
    summary: { total: 25, open: 4, critical: 1, important: 2, overdue: 1, closed: 21 },
  });
  assert.equal(response.items[0].pilotCode, "PIL-1405-001");
  assert.equal(response.page, 2);
  assert.equal(response.summary.total, 25);
});
