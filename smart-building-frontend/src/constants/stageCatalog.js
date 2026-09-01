export const STAGE_TITLES = Object.freeze({
  1: "انتخاب پروژه مناسب برای پایلوت",
  2: "معرفی و موافقت",
  3: "دریافت DWG و اطلاعات طبقات",
  4: "راه‌اندازی در پلتفرم اصلی",
  5: "برنامه‌ریزی و تخصیص مأموریت",
  6: "آمادگی قبل از برداشت",
  7: "اجرای برداشت طبقات",
  8: "کنترل نتیجه چندطبقه",
  9: "وضعیت Upload در پلتفرم اصلی",
  10: "کنترل پردازش در پلتفرم اصلی",
  11: "اطلاع‌رسانی آماده‌شدن بازدید",
  12: "آموزش اولیه مالک",
  13: "پیگیری پشتیبانی",
  14: "ادامه برداشت‌های پایلوت",
  15: "ارزیابی موفقیت پایلوت",
  16: "جلسه جمع‌بندی با مالک",
  17: "تهیه و ارائه پیشنهاد تجاری",
  18: "پیگیری تا تصمیم و عقد قرارداد",
  19: "تبدیل پایلوت به قرارداد یا بستن پرونده",
});

export const getStageTitle = (stageNumber, apiTitle = "") => {
  const number = Number(stageNumber);
  if (!Number.isInteger(number) || number < 1 || number > 19) return "مرحله نامشخص";
  const normalizedApiTitle = String(apiTitle ?? "").trim();
  return normalizedApiTitle || STAGE_TITLES[number] || "مرحله نامشخص";
};

export const stageOptions = () => Object.entries(STAGE_TITLES).map(([number, title]) => [number, title]);
