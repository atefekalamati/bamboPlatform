import { request } from "./httpClient.js";

const payload = (values) => ({
  project_reference: values.projectReference?.trim() || null,
  platform_status: values.platformStatus,
  processing_started: values.processingStarted,
  route_detected: values.routeDetected,
  plan_connected: values.planConnected,
  tour_ready: values.tourReady,
  captures_menu_checked: values.capturesMenuChecked,
  latest_capture_checked: values.latestCaptureChecked,
  last_visit_checked: values.lastVisitChecked,
  reason: values.reason?.trim() || null,
  checked_at: new Date(values.checkedAt).toISOString(),
});

export const experienceService = Object.freeze({
  getExternalPlatform: async (pilotId) => {
    try {
      return await request(`/pilots/${pilotId}/external-platform`);
    } catch (error) {
      if (error.status === 404) return null;
      throw error;
    }
  },
  saveExternalPlatform: (pilotId, values) =>
    request(`/pilots/${pilotId}/external-platform`, {
      method: "PUT",
      body: JSON.stringify(payload(values)),
    }),
  sendMainOutputNotification: (
    pilotId,
    { recipientMobile = "", alternateContactMethod = "" } = {},
  ) =>
    request(`/pilots/${pilotId}/notifications/main-output`, {
      method: "POST",
      body: JSON.stringify({
        recipient_mobile: recipientMobile.trim() || null,
        alternate_contact_method: alternateContactMethod.trim() || null,
      }),
    }),
  getF04: async (pilotId) => {
    try {
      return await request(`/pilots/${pilotId}/forms/f04`);
    } catch (error) {
      if (error.status === 404) return null;
      throw error;
    }
  },
  saveF04Training: (pilotId, values) =>
    request(`/pilots/${pilotId}/forms/f04`, {
      method: "PATCH",
      body: JSON.stringify({
        training_completed: values.capabilitiesIntroduced,
        more_training_needed: !values.independentUse,
        login_trained: values.loginAndProject,
        project_trained: values.loginAndProject,
        floor_trained: values.floorAndPlan,
        plan_trained: values.floorAndPlan,
        tour_trained: values.tourAndNavigation,
        navigation_trained: values.tourAndNavigation,
        support_trained: values.supportIntroduced,
        independent_use_confirmed: values.independentUse,
      }),
    }),
});
