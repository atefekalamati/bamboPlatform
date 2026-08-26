import { request } from "./httpClient.js";
import { API_BASE_PATHS } from "../config/apiRoutes.js";

const BASE = API_BASE_PATHS.reports;

export const buildReportQuery = (filters = {}) => {
  const query = new URLSearchParams();
  Object.entries(filters).forEach(([key, value]) => {
    if (value === "" || value === null || value === undefined) return;
    query.set(key, String(value));
  });
  const text = query.toString();
  return text ? `?${text}` : "";
};

const get = (path, filters, signal) => request(`${BASE}${path}${buildReportQuery(filters)}`, { signal });

export const reportService = Object.freeze({
  getOverview: (filters, signal) => get("/overview", filters, signal),
  getPipeline: (filters, signal) => get("/pipeline", filters, signal),
  getPilots: (filters, signal) => get("/pilots", filters, signal),
  getGates: (filters, signal) => get("/gates", filters, signal),
  getActions: (filters, signal) => get("/actions", filters, signal),
  getSla: (filters, signal) => get("/sla", filters, signal),
  getKpis: (filters, signal) => get("/kpis", filters, signal),
  getIncidents: (filters, signal) => get("/incidents", filters, signal),
  getOnePage: (pilotId, signal) => get(`/pilots/${encodeURIComponent(pilotId)}/one-page`, {}, signal),
  getExternalEvidence: (pilotId, signal) => get(`/pilots/${encodeURIComponent(pilotId)}/external-evidence`, {}, signal),
});

