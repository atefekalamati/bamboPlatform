import assert from "node:assert/strict";
import test from "node:test";
import { dashboardQueryString } from "../src/services/dashboardService.js";

test("serializes only supported non-empty dashboard filters", () => {
  assert.equal(dashboardQueryString({ page: 2, q: "BAMBO", stage: "", sla: null }), "?page=2&q=BAMBO");
});

test("encodes search values safely", () => {
  assert.equal(dashboardQueryString({ q: "پروژه یک" }), `?q=${encodeURIComponent("پروژه یک").replace(/%20/g, "+")}`);
});
