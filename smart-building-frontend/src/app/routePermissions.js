import { ROUTES } from "../constants/routes.js";

const EXACT = Object.freeze({
  [ROUTES.dashboard]: "dashboard.read",
  [ROUTES.pilots]: "pilots.read",
  [ROUTES.users]: "users.read",
  [ROUTES.roles]: "roles.read",
  [ROUTES.incidents]: "incidents.read",
  [ROUTES.notifications]: "notifications.read",
  [ROUTES.notificationSettings]: "notifications.read",
  [ROUTES.reports]: "reports.read",
  [ROUTES.reportPilots]: "reports.read",
  [ROUTES.reportActions]: "reports.read",
  [ROUTES.reportKpis]: "reports.read",
  [ROUTES.reportIncidents]: "reports.read",
});

export const requiredPermissionForRoute = (route) => {
  const path = route.split("?")[0];
  if (EXACT[path]) return EXACT[path];
  if (/^#\/reports\//.test(path)) return "reports.read";
  if (/^#\/incidents\//.test(path)) return "incidents.read";
  if (/^#\/pilots\/[^/]+\/incidents\/new$/.test(path)) return "incidents.manage";
  if (/^#\/pilots\//.test(path)) return "pilots.read";
  return null;
};

export const canAccessRoute = (route, permissions = []) => {
  const required = requiredPermissionForRoute(route);
  return !required || permissions.includes(required);
};

