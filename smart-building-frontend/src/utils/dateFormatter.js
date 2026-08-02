const IRAN_TIMEZONE = "Asia/Tehran";
const PERSIAN_LOCALE = "fa-IR-u-ca-persian";

const persianDateFormatter = new Intl.DateTimeFormat(PERSIAN_LOCALE, {
  timeZone: IRAN_TIMEZONE,
  year: "numeric",
  month: "long",
  day: "numeric",
});

const persianDateTimeFormatter = new Intl.DateTimeFormat(PERSIAN_LOCALE, {
  timeZone: IRAN_TIMEZONE,
  year: "numeric",
  month: "long",
  day: "numeric",
  hour: "2-digit",
  minute: "2-digit",
});

export const formatPersianDate = (isoDate) => {
  if (!isoDate) return "ثبت نشده";

  const date = new Date(isoDate);

  return Number.isNaN(date.getTime())
    ? "تاریخ نامعتبر"
    : persianDateFormatter.format(date);
};

export const formatPersianDateTime = (isoDate) => {
  if (!isoDate) return "ثبت نشده";

  const date = new Date(isoDate);

  return Number.isNaN(date.getTime())
    ? "تاریخ نامعتبر"
    : persianDateTimeFormatter.format(date);
};

