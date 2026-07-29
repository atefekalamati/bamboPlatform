export const ROUTES = Object.freeze({
  dashboard: "#/",
  pilots: "#/pilots",
  users: "#/users",
  roles: "#/roles",
  incidents: "#/incidents",
  reports: "#/reports",
  audit: "#/audit",
});

export const PRIMARY_NAVIGATION = Object.freeze([
  { label: "نمای کلی", href: ROUTES.dashboard, isAvailable: true },
  { label: "پرونده‌های پایلوت", href: ROUTES.pilots, isAvailable: true },
  { label: "کاربران", href: ROUTES.users, isAvailable: true },
  { label: "نقش‌ها و دسترسی‌ها", href: ROUTES.roles },
  { label: "رخدادها", href: ROUTES.incidents },
  { label: "گزارش‌ها", href: ROUTES.reports },
  { label: "تاریخچه تغییرات", href: ROUTES.audit },
]);
