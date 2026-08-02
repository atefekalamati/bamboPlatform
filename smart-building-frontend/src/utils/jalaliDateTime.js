const IRAN_TIMEZONE = "Asia/Tehran";
const PERSIAN_DIGITS = "۰۱۲۳۴۵۶۷۸۹";
const INPUT_PATTERN = /^(\d{4})[\/-](\d{1,2})[\/-](\d{1,2})(?:\s+(\d{1,2}):(?:(\d{1,2})))?$/;

const div = (a, b) => Math.trunc(a / b);
const mod = (a, b) => a - Math.trunc(a / b) * b;

const jalaliToGregorian = (jy, jm, jd) => {
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

export const toLatinDigits = (value) => String(value ?? "")
  .replace(/[۰-۹]/g, (digit) => String(PERSIAN_DIGITS.indexOf(digit)))
  .replace(/[٠-٩]/g, (digit) => String("٠١٢٣٤٥٦٧٨٩".indexOf(digit)));

const toPersianDigits = (value) => String(value).replace(/\d/g, (digit) => PERSIAN_DIGITS[Number(digit)]);
const pad = (value) => String(value).padStart(2, "0");

const formatter = new Intl.DateTimeFormat("en-US-u-ca-persian", {
  timeZone: IRAN_TIMEZONE,
  year: "numeric", month: "2-digit", day: "2-digit",
  hour: "2-digit", minute: "2-digit", hourCycle: "h23",
});

export const formatJalaliDateTimeInput = (value) => {
  if (!value) return "";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "";
  const parts = Object.fromEntries(formatter.formatToParts(date).map(({ type, value: part }) => [type, part]));
  return toPersianDigits(`${parts.year}/${parts.month}/${parts.day} ${parts.hour}:${parts.minute}`);
};

const timezoneOffsetAt = (utcMilliseconds) => {
  const parts = new Intl.DateTimeFormat("en-CA", {
    timeZone: IRAN_TIMEZONE, year: "numeric", month: "2-digit", day: "2-digit",
    hour: "2-digit", minute: "2-digit", second: "2-digit", hourCycle: "h23",
  }).formatToParts(new Date(utcMilliseconds));
  const values = Object.fromEntries(parts.map(({ type, value }) => [type, value]));
  const representedAsUtc = Date.UTC(+values.year, +values.month - 1, +values.day, +values.hour, +values.minute, +values.second);
  return representedAsUtc - utcMilliseconds;
};

export const parseJalaliDateTimeInput = (value) => {
  const match = toLatinDigits(value).trim().match(INPUT_PATTERN);
  if (!match) return null;
  const [, jy, jm, jd, hour = "0", minute = "0"] = match;
  const numbers = [jy, jm, jd, hour, minute].map(Number);
  if (numbers[1] < 1 || numbers[1] > 12 || numbers[2] < 1 || numbers[2] > 31 || numbers[3] > 23 || numbers[4] > 59) return null;
  const gregorian = jalaliToGregorian(numbers[0], numbers[1], numbers[2]);
  const localAsUtc = Date.UTC(gregorian.year, gregorian.month - 1, gregorian.day, numbers[3], numbers[4]);
  let utc = localAsUtc - timezoneOffsetAt(localAsUtc);
  utc = localAsUtc - timezoneOffsetAt(utc);
  const result = new Date(utc);
  return formatJalaliDateTimeInput(result) === toPersianDigits(`${jy}/${pad(jm)}/${pad(jd)} ${pad(hour)}:${pad(minute)}`)
    ? result.toISOString()
    : null;
};

const enhanceInput = (input) => {
  if (input.dataset.jalaliEnhanced === "true" || input.type !== "datetime-local") return;
  const inputValueDescriptor = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, "value");
  const initialValue = inputValueDescriptor.get.call(input);
  input.type = "text";
  input.dataset.jalaliEnhanced = "true";
  input.dataset.dateTimezone = IRAN_TIMEZONE;
  input.inputMode = "numeric";
  input.placeholder = "۱۴۰۵/۰۵/۱۲ ۱۴:۳۰";
  input.autocomplete = "off";
  inputValueDescriptor.set.call(input, formatJalaliDateTimeInput(initialValue));
  Object.defineProperty(input, "value", {
    configurable: true,
    get() {
      const visibleValue = inputValueDescriptor.get.call(this);
      if (!visibleValue.trim()) return "";
      return parseJalaliDateTimeInput(visibleValue) ?? "";
    },
    set(value) { inputValueDescriptor.set.call(this, formatJalaliDateTimeInput(value)); },
  });
  input.addEventListener("blur", () => {
    const visibleValue = inputValueDescriptor.get.call(input);
    if (!visibleValue.trim()) { input.setCustomValidity(""); return; }
    const parsed = parseJalaliDateTimeInput(visibleValue);
    input.setCustomValidity(parsed ? "" : "تاریخ را به قالب ۱۴۰۵/۰۵/۱۲ ۱۴:۳۰ وارد کنید.");
    if (parsed) inputValueDescriptor.set.call(input, formatJalaliDateTimeInput(parsed));
  });
  input.addEventListener("input", () => input.setCustomValidity(""));
};

export const enhanceJalaliDateTimeInputs = (root = document) => {
  if (root instanceof HTMLInputElement) enhanceInput(root);
  root.querySelectorAll?.('input[type="datetime-local"]').forEach(enhanceInput);
};

export const startJalaliDateTimeInputs = (root = document.documentElement) => {
  enhanceJalaliDateTimeInputs(root);
  const observer = new MutationObserver((mutations) => mutations.forEach((mutation) =>
    mutation.addedNodes.forEach((node) => {
      if (node instanceof Element) enhanceJalaliDateTimeInputs(node);
    })));
  observer.observe(root, { childList: true, subtree: true });
  return () => observer.disconnect();
};

export { IRAN_TIMEZONE };
