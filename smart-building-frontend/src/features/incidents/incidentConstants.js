export const INCIDENT_LABELS = Object.freeze({
  severity: Object.freeze({ normal: "عادی", important: "مهم", critical: "بحرانی" }),
  type: Object.freeze({ safety: "ایمنی", equipment: "تجهیزات", dwg: "فایل یا DWG", main_platform: "پلتفرم اصلی", access: "دسترسی", customer: "مشتری", process: "فرایند" }),
  status: Object.freeze({ open: "باز", contained: "مهارشده", resolved: "حل‌شده", closed: "بسته‌شده" }),
});

export const RESPONSE_TARGETS = Object.freeze({
  critical: "حداکثر ۳۰ دقیقه",
  important: "حداکثر ۴ ساعت کاری",
  normal: "همان روز کاری",
});

export const isIncidentOverdue = (incident, now = Date.now()) =>
  incident.status !== "closed" && new Date(incident.responseDueAt).getTime() < now;

export const incidentSlaState = (incident, now = Date.now()) => {
  if (incident.status === "closed") return { code: "completed", label: "تکمیل‌شده" };
  const due = new Date(incident.responseDueAt).getTime();
  if (!Number.isFinite(due)) return { code: "unknown", label: "نامشخص" };
  if (due < now) return { code: "overdue", label: "گذشته از مهلت" };
  if (due - now < 60 * 60 * 1000) return { code: "near", label: "نزدیک به مهلت" };
  return { code: "within", label: "در محدوده" };
};
