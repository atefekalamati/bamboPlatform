import assert from "node:assert/strict";
import test from "node:test";
import {
  defaultDateInputValue, formatIranDateTimeLocalValue, formatJalaliDateTimeInput, formatJalaliManualInput, jalaliMonthLength, parseJalaliDateInput, resolveDateInputValue,
  parseJalaliDateTimeInput, toBackendUtcDateTime,
} from "../src/utils/jalaliDateTime.js";

test("manual date entry accepts mixed digits and adds separators", () => {
  assert.equal(formatJalaliManualInput("۱۴۰5-٠٥.12"), "۱۴۰۵/۰۵/۱۲");
  assert.equal(formatJalaliManualInput("14050"), "۱۴۰۵/۰");
  assert.equal(formatJalaliManualInput("14050512345"), "۱۴۰۵/۰۵/۱۲");
});

test("manual date-time entry masks date, hour and minute", () => {
  assert.equal(formatJalaliManualInput("140505121430", true), "۱۴۰۵/۰۵/۱۲ ۱۴:۳۰");
});

test("a timezone-less backend control value is interpreted in Asia/Tehran", () => {
  assert.equal(formatJalaliDateTimeInput("2026-03-21T03:30"), "۱۴۰۵/۰۱/۰۱ ۰۳:۳۰");
  assert.equal(toBackendUtcDateTime("2026-08-08T14:30"), "2026-08-08T11:00:00.000Z");
  assert.equal(formatIranDateTimeLocalValue("2026-08-08T11:00:00.000Z"), "2026-08-08T14:30");
});

test("blank date controls resolve to the current Iran date/time only when read", () => {
  const now = new Date("2026-08-19T08:15:00.000Z");
  assert.equal(resolveDateInputValue("date", "", true, now), "2026-08-19");
  assert.equal(resolveDateInputValue("datetime-local", "", true, now), "2026-08-19T11:45");
  assert.equal(resolveDateInputValue("datetime-local", "2026-09-01T09:30", true, now), "2026-09-01T09:30");
  assert.equal(resolveDateInputValue("datetime-local", "", false, now), "");
});

test("empty date controls default to the current Iran date and time", () => {
  const now = new Date("2026-08-19T08:15:00.000Z");
  assert.equal(defaultDateInputValue("date", "", now), "2026-08-19");
  assert.equal(defaultDateInputValue("datetime-local", "", now), "2026-08-19T11:45");
});

test("a backend date remains the default instead of being replaced by now", () => {
  const now = new Date("2026-08-19T08:15:00.000Z");
  assert.equal(defaultDateInputValue("date", "2026-09-01", now), "2026-09-01");
  assert.equal(defaultDateInputValue("datetime-local", "2026-09-01T09:30", now), "2026-09-01T09:30");
});

test("Jalali validation rejects invalid month and day", () => {
  assert.equal(parseJalaliDateInput("۱۴۰۵/۱۳/۰۱"), null);
  assert.equal(parseJalaliDateInput("۱۴۰۵/۰۷/۳۱"), null);
  assert.equal(parseJalaliDateTimeInput("۱۴۰۵/۰۵/۱۲ ۲۴:۰۰"), null);
});

test("Esfand length follows the Jalali leap year", () => {
  assert.equal(jalaliMonthLength(1403, 12), 30);
  assert.equal(jalaliMonthLength(1404, 12), 29);
  assert.ok(parseJalaliDateInput("۱۴۰۳/۱۲/۳۰"));
  assert.equal(parseJalaliDateInput("۱۴۰۴/۱۲/۳۰"), null);
});
