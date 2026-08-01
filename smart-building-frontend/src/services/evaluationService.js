import { request } from "./httpClient.js";

export const evaluationService = Object.freeze({
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
