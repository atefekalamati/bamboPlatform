import { request, requestBlob, requestText } from "./httpClient.js";

export const formService = Object.freeze({
  listForms: (pilotId) => request(`/pilots/${pilotId}/forms`),
  getPreview: (href) => request(href),
  getPrintHtml: (href) => requestText(href),
  downloadPdf: (href) => requestBlob(href),
});
