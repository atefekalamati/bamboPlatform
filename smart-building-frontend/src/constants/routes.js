export const ROUTES = Object.freeze({
  dashboard: "#/",
  pilots: "#/pilots",
  users: "#/users",
  roles: "#/roles",
  incidents: "#/incidents",
  reports: "#/reports",
  audit: "#/audit",
  notifications: "#/notifications",
  notificationSettings: "#/settings/notifications",
});

export const PRIMARY_NAVIGATION = Object.freeze([
  { label: "نمای کلی", href: ROUTES.dashboard, isAvailable: true },
  { label: "پرونده‌های پایلوت", href: ROUTES.pilots, isAvailable: true },
  { label: "کاربران", href: ROUTES.users, isAvailable: true },
  {
    label: "نقش‌ها و دسترسی‌ها",
    href: ROUTES.roles,
    isAvailable: true,
  },
  { label: "رخدادها", href: ROUTES.incidents, isAvailable: true, permission: "incidents.read" },
  { label: "گزارش‌ها", href: ROUTES.reports },
  { label: "تاریخچه تغییرات", href: ROUTES.audit },
  { label: "اعلان‌ها", href: ROUTES.notifications, isAvailable: true, permission: "notifications.read" },
]);
