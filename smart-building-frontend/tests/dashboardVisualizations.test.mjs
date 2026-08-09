import assert from "node:assert/strict";
import test from "node:test";
import { canOpenStageFromDashboard, dashboardMetricValues, processCompletionPercent, stageProgressPercent } from "../src/components/DashboardVisualizations.js";

test("maps operational metrics without duplicating total pilots in the chart", () => {
  const values = dashboardMetricValues({ total_pilots: 2, active: 1, sla_overdue: 1 });
  assert.equal(values.length, 7);
  assert.equal(values.some(({ key }) => key === "total_pilots"), false);
  assert.equal(values.find(({ key }) => key === "contracted").value, 0);
});

test("normalizes invalid chart values and calculates approved stage progress", () => {
  assert.equal(dashboardMetricValues({ active: -3 })[0].value, 0);
  assert.equal(stageProgressPercent([{ status: "approved" }, { status: "approved" }, { status: "open" }]), 11);
  assert.equal(stageProgressPercent([]), 0);
});

test("uses only completed versus total pilots for the process ring", () => {
  assert.equal(processCompletionPercent({ total_pilots: 10, completed: 4, active: 9, sla_overdue: 8 }), 40);
  assert.equal(processCompletionPercent({ total_pilots: 0, completed: 4 }), 0);
  assert.equal(processCompletionPercent({ total_pilots: 3, completed: 9 }), 100);
});

test("only exposes an open stage as a dashboard navigation target", () => {
  assert.equal(canOpenStageFromDashboard({ status: "open" }), true);
  assert.equal(canOpenStageFromDashboard({ status: "approved" }), false);
  assert.equal(canOpenStageFromDashboard({ status: "locked" }), false);
  assert.equal(canOpenStageFromDashboard(null), false);
});
