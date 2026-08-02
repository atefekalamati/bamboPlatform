import assert from "node:assert/strict";
import test from "node:test";
import {
  formatJalaliDateTimeInput,
  parseJalaliDateTimeInput,
  toLatinDigits,
} from "../src/utils/jalaliDateTime.js";

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
