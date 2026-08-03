export const IRAN_TIMEZONE = "Asia/Tehran";
export const PERSIAN_MONTHS = ["فروردین", "اردیبهشت", "خرداد", "تیر", "مرداد", "شهریور", "مهر", "آبان", "آذر", "دی", "بهمن", "اسفند"];
export const PERSIAN_WEEKDAYS = ["ش", "ی", "د", "س", "چ", "پ", "ج"];
const PERSIAN_DIGITS = "۰۱۲۳۴۵۶۷۸۹";
const ARABIC_DIGITS = "٠١٢٣٤٥٦٧٨٩";
const div = (a, b) => Math.trunc(a / b);
const mod = (a, b) => a - Math.trunc(a / b) * b;
const pad = (value) => String(value).padStart(2, "0");

export const toLatinDigits = (value) => String(value ?? "")
  .replace(/[۰-۹]/g, (digit) => String(PERSIAN_DIGITS.indexOf(digit)))
  .replace(/[٠-٩]/g, (digit) => String(ARABIC_DIGITS.indexOf(digit)));

export const toPersianDigits = (value) => String(value ?? "").replace(/\d/g, (digit) => PERSIAN_DIGITS[Number(digit)]);

export const jalaliToGregorian = (jy, jm, jd) => {
  jy += 1595;
  let days = -355668 + (365 * jy) + (div(jy, 33) * 8) + div(mod(jy, 33) + 3, 4)
    + jd + (jm < 7 ? (jm - 1) * 31 : ((jm - 7) * 30) + 186);
  let gy = 400 * div(days, 146097);
  days = mod(days, 146097);
  if (days > 36524) {
    gy += 100 * div(--days, 36524);
    days = mod(days, 36524);
    if (days >= 365) days += 1;
  }
  gy += 4 * div(days, 1461);
  days = mod(days, 1461);
  if (days > 365) {
    gy += div(days - 1, 365);
    days = mod(days - 1, 365);
  }
  const gd = days + 1;
  const monthDays = [0, 31, (gy % 4 === 0 && gy % 100 !== 0) || gy % 400 === 0 ? 29 : 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31];
  let gm = 1;
  let day = gd;
  while (gm <= 12 && day > monthDays[gm]) day -= monthDays[gm++];
  return { year: gy, month: gm, day };
};

const dateFormatter = new Intl.DateTimeFormat("en-US-u-ca-persian", {
  timeZone: IRAN_TIMEZONE, year: "numeric", month: "2-digit", day: "2-digit",
});
const dateTimeFormatter = new Intl.DateTimeFormat("en-US-u-ca-persian", {
  timeZone: IRAN_TIMEZONE, year: "numeric", month: "2-digit", day: "2-digit",
  hour: "2-digit", minute: "2-digit", hourCycle: "h23",
});
const partsOf = (formatter, value) => Object.fromEntries(
  formatter.formatToParts(value).map(({ type, value: part }) => [type, part]),
);

export const getIranJalaliParts = (value = new Date()) => {
  const parts = partsOf(dateTimeFormatter, value);
  return { year: +parts.year, month: +parts.month, day: +parts.day, hour: +parts.hour, minute: +parts.minute };
};

export const formatJalaliDateInput = (value) => {
  if (!value) return "";
  const date = /^\d{4}-\d{2}-\d{2}$/.test(String(value)) ? new Date(`${value}T12:00:00Z`) : new Date(value);
  if (Number.isNaN(date.getTime())) return "";
  const parts = partsOf(dateFormatter, date);
  return toPersianDigits(`${parts.year}/${parts.month}/${parts.day}`);
};

export const formatJalaliDateTimeInput = (value) => {
  if (!value) return "";
  const naive = String(value).match(/^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2})(?::(\d{2}))?$/);
  let date;
  if (naive) {
    const [, year, month, day, hour, minute, second = "0"] = naive;
    const localAsUtc = Date.UTC(+year, +month - 1, +day, +hour, +minute, +second);
    let utc = localAsUtc - timezoneOffsetAt(localAsUtc);
    utc = localAsUtc - timezoneOffsetAt(utc);
    date = new Date(utc);
  } else date = new Date(value);
  if (Number.isNaN(date.getTime())) return "";
  const parts = partsOf(dateTimeFormatter, date);
  return toPersianDigits(`${parts.year}/${parts.month}/${parts.day} ${parts.hour}:${parts.minute}`);
};

export const parseJalaliDateInput = (value) => {
  const match = toLatinDigits(value).trim().match(/^(\d{4})[\/-](\d{1,2})[\/-](\d{1,2})$/);
  if (!match) return null;
  const [, jy, jm, jd] = match;
  const [year, month, day] = [jy, jm, jd].map(Number);
  if (month < 1 || month > 12 || day < 1 || day > 31) return null;
  const gregorian = jalaliToGregorian(year, month, day);
  const result = `${gregorian.year}-${pad(gregorian.month)}-${pad(gregorian.day)}`;
  return formatJalaliDateInput(result) === toPersianDigits(`${jy}/${pad(jm)}/${pad(jd)}`) ? result : null;
};

const timezoneOffsetAt = (utcMilliseconds) => {
  const parts = partsOf(new Intl.DateTimeFormat("en-CA", {
    timeZone: IRAN_TIMEZONE, year: "numeric", month: "2-digit", day: "2-digit",
    hour: "2-digit", minute: "2-digit", second: "2-digit", hourCycle: "h23",
  }), new Date(utcMilliseconds));
  return Date.UTC(+parts.year, +parts.month - 1, +parts.day, +parts.hour, +parts.minute, +parts.second) - utcMilliseconds;
};

export const parseJalaliDateTimeInput = (value) => {
  const match = toLatinDigits(value).trim().match(/^(\d{4})[\/-](\d{1,2})[\/-](\d{1,2})\s+(\d{1,2}):(\d{1,2})$/);
  if (!match) return null;
  const [, jy, jm, jd, hour, minute] = match;
  const numbers = [jy, jm, jd, hour, minute].map(Number);
  if (numbers[1] < 1 || numbers[1] > 12 || numbers[2] < 1 || numbers[2] > 31 || numbers[3] > 23 || numbers[4] > 59) return null;
  const gregorian = jalaliToGregorian(numbers[0], numbers[1], numbers[2]);
  const localAsUtc = Date.UTC(gregorian.year, gregorian.month - 1, gregorian.day, numbers[3], numbers[4]);
  let utc = localAsUtc - timezoneOffsetAt(localAsUtc);
  utc = localAsUtc - timezoneOffsetAt(utc);
  const result = new Date(utc);
  return formatJalaliDateTimeInput(result) === toPersianDigits(`${jy}/${pad(jm)}/${pad(jd)} ${pad(hour)}:${pad(minute)}`)
    ? result.toISOString() : null;
};

export const formatJalaliManualInput = (value, dateTime = false) => {
  const digits = toLatinDigits(value).replace(/\D/g, "").slice(0, dateTime ? 12 : 8);
  const date = [digits.slice(0, 4), digits.slice(4, 6), digits.slice(6, 8)].filter(Boolean).join("/");
  if (!dateTime || digits.length <= 8) return toPersianDigits(date);
  const hour = digits.slice(8, 10);
  const minute = digits.slice(10, 12);
  return toPersianDigits(`${date} ${hour}${minute ? `:${minute}` : ""}`);
};

export const jalaliMonthLength = (year, month) => {
  if (month <= 6) return 31;
  if (month <= 11) return 30;
  return parseJalaliDateInput(`${year}/12/30`) ? 30 : 29;
};

export const jalaliWeekdayIndex = (year, month, day = 1) => {
  const gregorian = jalaliToGregorian(year, month, day);
  return (new Date(Date.UTC(gregorian.year, gregorian.month - 1, gregorian.day)).getUTCDay() + 1) % 7;
};
