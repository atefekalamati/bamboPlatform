export const ROUTES = Object.freeze({
  dashboard: "#/",
  pilots: "#/pilots",
  users: "#/users",
  roles: "#/roles",
  incidents: "#/incidents",
  reports: "#/reports",
  reportPilots: "#/reports/pilots",
  reportActions: "#/reports/actions",
  reportKpis: "#/reports/kpis",
  reportIncidents: "#/reports/incidents",
  audit: "#/audit",
  notifications: "#/notifications",
  notificationSettings: "#/settings/notifications",
});

export const PRIMARY_NAVIGATION = Object.freeze([
  { label: "نمای کلی", href: ROUTES.dashboard, isAvailable: true, permission: "dashboard.read" },
  { label: "پرونده‌های پایلوت", href: ROUTES.pilots, isAvailable: true, permission: "pilots.read" },
  { label: "کاربران", href: ROUTES.users, isAvailable: true, permission: "users.read" },
  {
    label: "نقش‌ها و دسترسی‌ها",
    href: ROUTES.roles,
    isAvailable: true,
    permission: "roles.read",
    allowedRoles: ["admin", "super_admin"],
  },
  { label: "رخدادها", href: ROUTES.incidents, isAvailable: true, permission: "incidents.read" },
  { label: "گزارش‌ها", href: ROUTES.reports, isAvailable: true, permission: "reports.read" },
  { label: "تاریخچه تغییرات", href: ROUTES.audit },
  { label: "اعلان‌ها", href: ROUTES.notifications, isAvailable: true, permission: "notifications.read" },
]);
