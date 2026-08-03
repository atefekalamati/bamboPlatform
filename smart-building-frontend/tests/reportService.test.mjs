import assert from "node:assert/strict";
import test from "node:test";
import { buildReportQuery } from "../src/services/reportService.js";

test("serializes report filters and removes empty values", () => {
  assert.equal(buildReportQuery({ stage: 9, q: "پروژه یک", gate: "", page: 2 }), `?stage=9&q=${encodeURIComponent("پروژه یک").replace(/%20/g, "+")}&page=2`);
});

test("preserves backend report boolean and date filters", () => {
  assert.equal(buildReportQuery({ has_open_incident: false, date_from: "2026-08-01T00:00:00+03:30" }), "?has_open_incident=false&date_from=2026-08-01T00%3A00%3A00%2B03%3A30");
});

