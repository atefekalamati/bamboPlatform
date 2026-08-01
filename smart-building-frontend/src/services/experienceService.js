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
  saveF04FollowUp: (pilotId, values) =>
    request(`/pilots/${pilotId}/forms/f04`, {
      method: "PATCH",
      body: JSON.stringify({
        owner_logged_in: values.ownerLoggedIn,
        project_opened: values.projectOpened,
        main_tour_viewed: values.mainTourViewed,
        viewing_result: values.viewingResult || null,
        first_follow_up_at: values.firstFollowUpAt
          ? new Date(values.firstFollowUpAt).toISOString()
          : null,
        second_follow_up_at: values.secondFollowUpAt
          ? new Date(values.secondFollowUpAt).toISOString()
          : null,
        useful: values.useful,
        coverage_score: values.coverageScore || null,
        quality_score: values.qualityScore || null,
        most_useful_part: values.mostUsefulPart || null,
        missing_part: values.missingPart || null,
        other_users: values.otherUsers || null,
        more_training_needed: values.moreTrainingNeeded,
        satisfaction_score: values.satisfactionScore || null,
        issue_description: values.issueDescription || null,
        issue_category: values.issueCategory || null,
        issue_route: values.issueRoute || null,
        issue_owner_user_id: values.issueOwnerUserId || null,
        issue_due_at: values.issueDueAt
          ? new Date(values.issueDueAt).toISOString()
          : null,
        customer_success_user_id: values.customerSuccessUserId || null,
      }),
    }),
  saveF04Closing: (pilotId, values) =>
    request(`/pilots/${pilotId}/forms/f04`, {
      method: "PATCH",
      body: JSON.stringify({
        main_platform_login_count: Number(values.loginCount),
        viewed_sections: values.viewedSections,
        visit_reduction_result: values.visitReductionResult,
        customer_need_summary: values.customerNeedSummary,
        closing_decision: values.closingDecision,
        realized_value: values.realizedValue,
        purchase_blocker: values.purchaseBlocker,
        project_count: Number(values.projectCount),
        usage_frequency: values.usageFrequency,
        user_count: Number(values.userCount),
        decision_maker: values.decisionMaker,
      }),
    }),
  getIncidents: (pilotId) => request(`/pilots/${pilotId}/incidents`),
  closeIncident: (incidentId, values) =>
    request(`/incidents/${incidentId}/close`, {
      method: "POST",
      body: JSON.stringify({
        root_cause: values.rootCause,
        corrective_action: values.correctiveAction,
        result: values.result,
        evidence: values.evidence || null,
        lessons_learned: values.lessonsLearned,
        confirmed: true,
      }),
    }),
});
