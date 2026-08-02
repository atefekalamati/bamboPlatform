import { request } from "./httpClient.js";

export const preferenceService = Object.freeze({
  getPreferences: () => request("/auth/preferences"),
  updatePreferences: (values) =>
    request("/auth/preferences", {
      method: "PATCH",
      body: JSON.stringify(values),
    }),
});
