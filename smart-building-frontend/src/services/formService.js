import { sessionStore } from "../app/sessionStore.js";
import { APP_CONFIG } from "../config/appConfig.js";
import { request, requestBlob } from "./httpClient.js";

const requestUrl = (path) => `${APP_CONFIG.apiBaseUrl}${path}`;

const authorizedFetch = async (path) => {
  const token = sessionStore.getToken();
  const response = await fetch(requestUrl(path), {
    headers: {
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
  });

  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    throw new Error(payload.message ?? "دریافت فرم انجام نشد.");
  }

  return response;
};

export const formService = Object.freeze({
  listForms: (pilotId) => request(`/pilots/${pilotId}/forms`),
  getPreview: (href) => request(href),
  getPrintHtml: async (href) => (await authorizedFetch(href)).text(),
  downloadPdf: (href) => requestBlob(href),
});
