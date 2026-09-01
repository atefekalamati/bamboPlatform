import { request } from "./httpClient.js";
import { API_BASE_PATHS } from "../config/apiRoutes.js";

const DASHBOARD_BASE = API_BASE_PATHS.dashboard;
const BREAKDOWNS = new Set(["stages", "gates", "missions", "incidents", "sla", "forms", "commercial", "activities"]);

export const dashboardQueryString = (params = {}) => {
  const query = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== "") query.set(key, String(value));
  });
  const value = query.toString();
  return value ? `?${value}` : "";
};

const get = (path, { signal, params } = {}) =>
  request(`${DASHBOARD_BASE}${path}${dashboardQueryString(params)}`, { signal });

const breakdown = (kind, options) => {
  if (!BREAKDOWNS.has(kind)) throw new TypeError(`Unsupported dashboard breakdown: ${kind}`);
  return get(`/${kind}`, options);
};

export const dashboardService = Object.freeze({
  getSummary: (options) => get("/summary", options),
  getPilots: (params, options = {}) => get("/pilots", { ...options, params }),
  getMyActions: (options) => get("/my-actions", options),
  getStageSummary: (options) => breakdown("stages", options),
  getGateSummary: (options) => breakdown("gates", options),
  getMissionSummary: (options) => breakdown("missions", options),
  getIncidentSummary: (options) => breakdown("incidents", options),
  getSlaSummary: (options) => breakdown("sla", options),
  getFormsSummary: (options) => breakdown("forms", options),
  getCommercialSummary: (options) => breakdown("commercial", options),
  getRecentActivities: (options) => breakdown("activities", options),
});
