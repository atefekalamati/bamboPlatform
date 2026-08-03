import assert from "node:assert/strict";
import test from "node:test";
import {
  formatJalaliDateInput,
  formatJalaliDateTimeInput,
  parseJalaliDateInput,
  parseJalaliDateTimeInput,
  toLatinDigits,
} from "../src/utils/jalaliDateTime.js";

test("formats a backend date-only value as Jalali without a time", () => {
  assert.equal(formatJalaliDateInput("2026-03-21"), "۱۴۰۵/۰۱/۰۱");
});

test("parses a Jalali date-only value to the backend date contract", () => {
  assert.equal(parseJalaliDateInput("۱۴۰۵/۰۱/۰۱"), "2026-03-21");
});

test("rejects an invalid Jalali date-only value", () => {
  assert.equal(parseJalaliDateInput("۱۴۰۵/۰۱/۳۲"), null);
});

test("formats an instant as Jalali date in Iran timezone", () => {
  assert.equal(formatJalaliDateTimeInput("2026-03-21T00:00:00Z"), "۱۴۰۵/۰۱/۰۱ ۰۳:۳۰");
});

test("parses Persian Jalali input into a timezone-aware UTC instant", () => {
  assert.equal(parseJalaliDateTimeInput("۱۴۰۵/۰۱/۰۱ ۰۳:۳۰"), "2026-03-21T00:00:00.000Z");
});

test("rejects invalid Jalali dates", () => {
  assert.equal(parseJalaliDateTimeInput("۱۴۰۵/۱۳/۰۱ ۱۰:۰۰"), null);
  assert.equal(parseJalaliDateTimeInput("۱۴۰۵/۰۱/۳۲ ۱۰:۰۰"), null);
});

test("normalizes Persian and Arabic digits", () => {
  assert.equal(toLatinDigits("۱۴۰۵/٠٥/۱۲"), "1405/05/12");
});
