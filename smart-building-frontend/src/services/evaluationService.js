import { request } from "./httpClient.js";
import { toBackendUtcDateTime } from "../utils/jalaliDateTime.js";

export const evaluationService = Object.freeze({
  getEvaluation: async (pilotId) => {
    try {
      return await request(`/pilots/${pilotId}/evaluation`);
    } catch (error) {
      if (error.status === 404) return null;
      throw error;
    }
  },
  saveEvaluation: (pilotId, values) =>
    request(`/pilots/${pilotId}/evaluation`, {
      method: "PUT",
      body: JSON.stringify({
        operations_status: values.operationsStatus,
        operations_result: values.operationsResult,
        quality_status: values.qualityStatus,
        quality_result: values.qualityResult,
        technical_status: values.technicalStatus,
        technical_result: values.technicalResult,
        customer_status: values.customerStatus,
        customer_result: values.customerResult,
        commercial_status: values.commercialStatus,
        commercial_result: values.commercialResult,
        one_page_summary: values.onePageSummary,
      }),
    }),
  getExternalEvidence: (pilotId) =>
    request(`/pilots/${pilotId}/external-evidence`),
  saveExternalEvidence: (pilotId, capability, values) =>
    request(`/pilots/${pilotId}/external-evidence/${capability}`, {
      method: "PUT",
      body: JSON.stringify({
        status: values.status,
        checked_at: toBackendUtcDateTime(values.checkedAt),
        result: values.result?.trim() || null,
      }),
    }),
  getContinuationReview: async (missionId) => {
    try {
      return await request(`/missions/${missionId}/continuation-review`);
    } catch (error) {
      if (error.status === 404) return null;
      throw error;
    }
  },
  saveContinuationReview: (missionId, values) =>
    request(`/missions/${missionId}/continuation-review`, {
      method: "PUT",
      body: JSON.stringify({
        ...Object.fromEntries(
          Array.from({ length: 9 }, (_, index) => {
            const number = index + 5;
            return [`stage_${number}_confirmed`, values[`stage${number}`]];
          }),
        ),
        independent_result: values.independentResult,
      }),
    }),
});
