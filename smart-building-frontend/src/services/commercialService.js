import { request } from "./httpClient.js";

export const commercialService = Object.freeze({
  getFinalOutcome: async (pilotId) => {
    try {
      return await request(`/pilots/${pilotId}/final-outcome`);
    } catch (error) {
      if (error.status === 404) return null;
      throw error;
    }
  },
  saveFinalOutcome: (pilotId, values) =>
    request(`/pilots/${pilotId}/final-outcome`, {
      method: "PUT",
      body: JSON.stringify({
        outcome: values.outcome,
        reason: values.reason || null,
        ready_at: values.readyAt ? new Date(values.readyAt).toISOString() : null,
        success_owner_user_id: values.successOwnerUserId ? Number(values.successOwnerUserId) : null,
        periodic_capture: values.periodicCapture,
        contracted_user_count: values.contractedUserCount ? Number(values.contractedUserCount) : null,
        first_capture_at: values.firstCaptureAt ? new Date(values.firstCaptureAt).toISOString() : null,
      }),
    }),
  approveFinalOutcome: (pilotId) =>
    request(`/pilots/${pilotId}/final-outcome/approve`, {
      method: "POST",
      body: JSON.stringify({ confirmed: true }),
    }),
  getFollowUps: (pilotId) => request(`/pilots/${pilotId}/commercial-follow-ups`),
  saveFollowUp: (pilotId, slot, values) =>
    request(`/pilots/${pilotId}/commercial-follow-ups/${slot}`, {
      method: "PUT",
      body: JSON.stringify({
        obstacle: values.obstacle,
        action: values.action,
        owner_user_id: Number(values.ownerUserId),
        due_at: new Date(values.dueAt).toISOString(),
        result: values.result,
        completed_at: new Date(values.completedAt).toISOString(),
      }),
    }),
  getProposal: async (pilotId) => {
    try {
      return await request(`/pilots/${pilotId}/commercial-proposal`);
    } catch (error) {
      if (error.status === 404) return null;
      throw error;
    }
  },
  saveProposal: (pilotId, values) =>
    request(`/pilots/${pilotId}/commercial-proposal`, {
      method: "PUT",
      body: JSON.stringify({
        project_count: Number(values.projectCount),
        floor_count: Number(values.floorCount),
        area_sqm: Number(values.areaSqm),
        frequency: values.frequency,
        period: values.period,
        user_count: Number(values.userCount),
        support_scope: values.supportScope,
        features: values.features,
        proposal_file_name: values.fileName,
        proposal_file_size: values.fileSize,
        proposal_file_sha256: values.fileSha256,
        decision_maker: values.decisionMaker,
        follow_up_at: new Date(values.followUpAt).toISOString(),
      }),
    }),
});
