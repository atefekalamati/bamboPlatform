import { request } from "./httpClient.js";

const mapNotification = (notification) => ({
  id: notification.id,
  status: notification.status,
  providerStatus: notification.provider_status,
  lastError: notification.last_error,
  sentAt: notification.sent_at,
});

const mapMission = (mission) => ({
  id: mission.id,
  pilotId: mission.pilot_id,
  sequence: mission.sequence,
  code: mission.code,
  expertUserId: mission.expert_user_id,
  scheduledStart: mission.scheduled_start,
  scheduledEnd: mission.scheduled_end,
  location: mission.location,
  siteContactName: mission.site_contact_name,
  siteContactMobile: mission.site_contact_mobile,
  limitation: mission.limitation,
  status: mission.status,
  slaDueAt: mission.sla_due_at,
  floorStates: mission.floor_states,
  formF03: mission.form_f03,
  notifications: mission.notifications.map(mapNotification),
});

const f03Payload = (form) => ({
  assignment_accepted: form.assignment_accepted,
  site_entry_confirmed: form.site_entry_confirmed,
  permission_confirmed: form.permission_confirmed,
  ppe_ready: form.ppe_ready,
  camera_ready: form.camera_ready,
  main_app_connected: form.main_app_connected,
  battery_ready: form.battery_ready,
  storage_ready: form.storage_ready,
  project_floor_plan_confirmed: form.project_floor_plan_confirmed,
  test_image_completed: form.test_image_completed,
  stop_condition_reason: form.stop_condition_reason,
  mission_completed: form.mission_completed,
  operations_confirmed: form.operations_confirmed,
  started_at: form.started_at,
  finished_at: form.finished_at,
});

export const missionService = Object.freeze({
  getCaptureExperts: () => request("/missions/capture-experts"),
  getMissions: async (pilotId) =>
    (await request(`/pilots/${pilotId}/missions`)).map(mapMission),
  createMission: async (pilotId, values) =>
    mapMission(
      await request(`/pilots/${pilotId}/missions`, {
        method: "POST",
        body: JSON.stringify({
          expert_user_id: Number(values.expertUserId),
          scheduled_start: new Date(values.scheduledStart).toISOString(),
          scheduled_end: new Date(values.scheduledEnd).toISOString(),
          floor_ids: values.floorIds.map(Number),
          location: values.location,
          site_contact_name: values.siteContactName,
          site_contact_mobile: values.siteContactMobile,
          limitation: values.limitation || null,
        }),
      }),
    ),
  acceptAssignment: (mission) =>
    request(`/missions/${mission.id}/forms/f03`, {
        method: "PUT",
        body: JSON.stringify(
          f03Payload({ ...mission.formF03, assignment_accepted: true }),
        ),
      }),
  saveF03: (missionId, values) =>
    request(`/missions/${missionId}/forms/f03`, {
      method: "PUT",
      body: JSON.stringify(f03Payload(values)),
    }),
});
