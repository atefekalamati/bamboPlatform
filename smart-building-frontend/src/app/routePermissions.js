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

const ADMIN_ROLE_NAMES = new Set(["admin", "super_admin"]);

export const hasAdministrativeRole = (roles = []) =>
  roles.some((role) => ADMIN_ROLE_NAMES.has(typeof role === "string" ? role : role?.name));

export const canAccessRoute = (route, permissions = [], roles = []) => {
  const required = requiredPermissionForRoute(route);
  if (required && !permissions.includes(required)) return false;
  if (route.split("?")[0] === ROUTES.roles) return hasAdministrativeRole(roles);
  return true;
};

/**
 * Why a route was refused, in words the person can act on.
 *
 * A brand-new account signs in with no roles at all. Telling that person their
 * account lacks "dashboard.read" names an internal code they cannot do anything
 * about, and offering them a link back to the dashboard sends them to the page
 * that just refused them. Say what actually happened and who can fix it.
 */
export const accessDeniedReason = (route, permissions = [], roles = []) => {
  if (!roles.length) {
    return {
      title: "هنوز نقشی برای حساب شما تعیین نشده است",
      message:
        "حساب شما ساخته شده است، اما تا زمانی که مدیر سامانه نقشی برای شما تعیین نکند بخشی از سامانه در دسترس نیست.",
      returnRoute: null,
    };
  }

  const required = requiredPermissionForRoute(route);
  return {
    title: "دسترسی به این صفحه امکان‌پذیر نیست",
    message: `مجوز لازم برای این مسیر (${required ?? "نامشخص"}) در حساب شما وجود ندارد.`,
    // Only offer the dashboard when it is somewhere they can actually go.
    returnRoute: canAccessRoute(ROUTES.dashboard, permissions, roles) ? ROUTES.dashboard : null,
  };
};

