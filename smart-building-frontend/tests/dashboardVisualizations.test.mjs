import assert from "node:assert/strict";
import test from "node:test";
import { dashboardMetricValues, stageProgressPercent } from "../src/components/DashboardVisualizations.js";

test("maps all dashboard summary metrics without sample values", () => {
  const values = dashboardMetricValues({ total_pilots: 2, active: 1, sla_overdue: 1 });
  assert.equal(values.length, 8);
  assert.equal(values.find(({ key }) => key === "total_pilots").value, 2);
  assert.equal(values.find(({ key }) => key === "contracted").value, 0);
});

test("normalizes invalid chart values and calculates approved stage progress", () => {
  assert.equal(dashboardMetricValues({ active: -3 })[1].value, 0);
  assert.equal(stageProgressPercent([{ status: "approved" }, { status: "approved" }, { status: "open" }]), 11);
  assert.equal(stageProgressPercent([]), 0);
});
