const LABELS = Object.freeze({
  open: "باز", submitted: "ارسال‌شده", approved: "تأییدشده", needs_revision: "نیازمند اصلاح",
  locked: "قفل‌شده", active: "فعال", inactive: "غیرفعال", pending: "در انتظار", waiting: "در انتظار اقدام",
  draft: "پیش‌نویس", rejected: "ردشده", cancelled: "لغوشده", completed: "تکمیل‌شده", complete: "تکمیل‌شده",
  closed: "بسته‌شده", resolved: "حل‌شده", contained: "مهارشده", failed: "ناموفق", success: "موفق",
  on_track: "در مسیر", at_risk: "نزدیک موعد", overdue: "معوق", not_applicable: "بدون مهلت خدمت",
  scheduled: "برنامه‌ریزی‌شده", assigned: "تخصیص‌یافته", ready: "آماده", in_progress: "در حال انجام",
  normal: "عادی", low: "کم", medium: "متوسط", high: "مهم", important: "مهم", critical: "بحرانی",
  contract: "قرارداد", contracted: "قراردادشده", negotiation: "در حال مذاکره", ready_on_date: "آماده در تاریخ",
  proposal: "ارسال پیشنهاد", follow_up: "پیگیری", continue_pilot: "ادامه پایلوت", stop: "توقف", undecided: "تصمیم‌گیری‌نشده",
  review: "بازبینی مرحله", review_stage: "بازبینی مرحله", complete_stage: "تکمیل مرحله", submit_stage: "ارسال مرحله",
  mission: "مأموریت", incident: "رخداد", stage: "مرحله", gate: "گیت", form: "فرم", customer_follow_up: "پیگیری مشتری",
  missions: "مأموریت", incidents: "رخداد", stages: "مرحله", gates: "گیت", forms: "فرم", pilots: "پرونده", notifications: "اعلان",
  created: "ایجاد شد", updated: "به‌روزرسانی شد", deleted: "حذف شد", saved: "ذخیره شد",
  no_access: "بدون دسترسی", no_data: "بدون داده",
});

const ACTION_TITLES = Object.freeze({
  "mission requires action": "مأموریت نیازمند اقدام",
  "incident requires action": "رخداد نیازمند اقدام",
  "customer follow-up": "پیگیری مشتری",
  "customer follow up": "پیگیری مشتری",
  "complete stage": "تکمیل مرحله",
  "review stage": "بازبینی مرحله",
  "approve stage": "تأیید مرحله",
  "reject stage": "رد مرحله",
  "submit stage": "ارسال مرحله",
  "complete form": "تکمیل فرم",
  "review form": "بازبینی فرم",
  "resolve incident": "رسیدگی به رخداد",
  "close incident": "بستن رخداد",
});

const normalize = (value) => String(value ?? "").trim().toLowerCase();
const keyOf = (value) => normalize(value).replace(/[\s.-]+/g, "_");
const containsPersian = (value) => /[\u0600-\u06ff]/.test(value);

export const translateDisplayValue = (value, fallback = "—") => {
  if (value === null || value === undefined || value === "") return fallback;
  const text = String(value).trim();
  if (containsPersian(text)) return text;
  const key = keyOf(text);
  if (LABELS[key]) return LABELS[key];
  const gate = text.match(/^G([1-5])$/i);
  if (gate) return `گیت ${gate[1]}`;
  return /^[a-z][a-z0-9_. -]*$/i.test(text) ? fallback : text;
};

export const translateActionTitle = (value, fallback = "اقدام موردنیاز") => {
  if (!value) return fallback;
  const text = String(value).trim();
  if (containsPersian(text)) return text;
  const normalized = normalize(text).replace(/[_-]+/g, " ").replace(/\s+/g, " ");
  const stageAction = normalized.match(/^(complete|review|approve|reject|submit) stage\s*(\d+)?$/);
  if (stageAction) {
    const verbs = { complete: "تکمیل", review: "بازبینی", approve: "تأیید", reject: "رد", submit: "ارسال" };
    return `${verbs[stageAction[1]]} مرحله${stageAction[2] ? ` ${stageAction[2]}` : ""}`;
  }
  return ACTION_TITLES[normalized] ?? translateDisplayValue(text, fallback);
};

export const translateAuditAction = (value) => {
  if (!value) return "فعالیت ثبت‌شده";
  const text = String(value).trim();
  if (containsPersian(text)) return text;
  const parts = keyOf(text).split("_");
  const translated = parts.map((part) => LABELS[part]).filter(Boolean);
  return translated.length >= Math.min(2, parts.length) ? translated.join(" — ") : "فعالیت ثبت‌شده";
};

export const displayLabels = LABELS;
