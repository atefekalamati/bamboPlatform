import { request } from "./httpClient.js";

const mapF01 = (form) => ({
  id: form.id,
  projectActive: form.project_active,
  imagingValue: form.imaging_value,
  remoteViewingNeed: form.remote_viewing_need,
  accessPossible: form.access_possible,
  dwgAvailable: form.dwg_available,
  continuedCapacity: form.continued_capacity,
  notDemoOnly: form.not_demo_only,
  introductionCompleted: form.introduction_completed,
  imagingAccepted: form.imaging_accepted,
  dwgAccepted: form.dwg_accepted,
  feedbackAccepted: form.feedback_accepted,
  coordinatorName: form.coordinator_name,
  coordinatorMobile: form.coordinator_mobile,
  limitation: form.limitation,
  result: form.result,
  referralDeadline: form.referral_deadline,
  salesUserId: form.sales_user_id,
  pilotManagerUserId: form.pilot_manager_user_id,
  referredAt: form.referred_at,
  updatedAt: form.updated_at,
});

const f01Payload = (values) => ({
  project_active: values.projectActive,
  imaging_value: values.imagingValue,
  remote_viewing_need: values.remoteViewingNeed,
  access_possible: values.accessPossible,
  dwg_available: values.dwgAvailable,
  continued_capacity: values.continuedCapacity,
  not_demo_only: values.notDemoOnly,
  introduction_completed: values.introductionCompleted ?? false,
  imaging_accepted: values.imagingAccepted ?? false,
  dwg_accepted: values.dwgAccepted ?? false,
  feedback_accepted: values.feedbackAccepted ?? false,
  coordinator_name: values.coordinatorName || null,
  coordinator_mobile: values.coordinatorMobile || null,
  limitation: values.limitation || null,
  result: values.result,
  referral_deadline: values.referralDeadline || null,
  sales_user_id: values.salesUserId || null,
  pilot_manager_user_id: values.pilotManagerUserId || null,
  referred_at: values.referredAt || null,
});

const mapF02 = (form) => ({
  id: form.id,
  informationPackage: form.information_package,
  contactsSummary: form.contacts_summary,
  progressStatus: form.progress_status,
  limitation: form.limitation,
  mainProjectRegistered: form.main_project_registered,
  floorOrderConfirmed: form.floor_order_confirmed,
  typicalFloorsIdentified: form.typical_floors_identified,
  planConnectionsRegistered: form.plan_connections_registered,
  startPointRegistered: form.start_point_registered,
  expertAccessTested: form.expert_access_tested,
  mainAppDisplayTested: form.main_app_display_tested,
  readyForCapture: form.ready_for_capture,
  ambiguity: form.ambiguity,
  referredAt: form.referred_at,
  configuredByUserId: form.configured_by_user_id,
  controlledByUserId: form.controlled_by_user_id,
  configuredAt: form.configured_at,
  responsibleUserId: form.responsible_user_id,
  updatedAt: form.updated_at,
});

const f02Payload = (values) => ({
  information_package: values.informationPackage || null,
  contacts_summary: values.contactsSummary || null,
  progress_status: values.progressStatus || null,
  limitation: values.limitation || null,
  main_project_registered: values.mainProjectRegistered ?? false,
  floor_order_confirmed: values.floorOrderConfirmed ?? false,
  typical_floors_identified: values.typicalFloorsIdentified ?? false,
  plan_connections_registered: values.planConnectionsRegistered ?? false,
  start_point_registered: values.startPointRegistered ?? false,
  expert_access_tested: values.expertAccessTested ?? false,
  main_app_display_tested: values.mainAppDisplayTested ?? false,
  ready_for_capture: values.readyForCapture ?? false,
  ambiguity: values.ambiguity || null,
  referred_at: values.referredAt || null,
  configured_by_user_id: values.configuredByUserId || null,
  controlled_by_user_id: values.controlledByUserId || null,
  configured_at: values.configuredAt || null,
});

export const stageService = Object.freeze({
  getF01: async (pilotId) => {
    try {
      return mapF01(await request(`/pilots/${pilotId}/forms/f01`));
    } catch (error) {
      if (error.status === 404) return null;
      throw error;
    }
  },
  saveF01: async (pilotId, values) =>
    mapF01(
      await request(`/pilots/${pilotId}/forms/f01`, {
        method: "PUT",
        body: JSON.stringify(f01Payload(values)),
      }),
    ),
  getF02: async (pilotId) => {
    try {
      return mapF02(await request(`/pilots/${pilotId}/forms/f02`));
    } catch (error) {
      if (error.status === 404) return null;
      throw error;
    }
  },
  saveF02: async (pilotId, values) =>
    mapF02(
      await request(`/pilots/${pilotId}/forms/f02`, {
        method: "PUT",
        body: JSON.stringify(f02Payload(values)),
      }),
    ),
  submit: (pilotId, stageNumber) =>
    request(`/pilots/${pilotId}/stages/${stageNumber}/submit`, {
      method: "POST",
      body: JSON.stringify({ form_data: {}, checklist: {} }),
    }),
  approve: (pilotId, stageNumber, comment = "") =>
    request(`/pilots/${pilotId}/stages/${stageNumber}/approve`, {
      method: "POST",
      body: JSON.stringify({ comment: comment || null }),
    }),
  reject: (pilotId, stageNumber, { reason, correctionItems }) =>
    request(`/pilots/${pilotId}/stages/${stageNumber}/reject`, {
      method: "POST",
      body: JSON.stringify({
        reason: reason || null,
        correction_items: correctionItems,
      }),
    }),
  getSnapshots: (pilotId, stageNumber) =>
    request(`/pilots/${pilotId}/stages/${stageNumber}/snapshots`),
});
