import assert from "node:assert/strict";
import test from "node:test";
import { getStageRoute } from "../src/features/stages/stageNavigation.js";

test("available Stage cards use the same direct route as the detail action", () => {
  for (const status of ["open", "submitted", "needs_revision", "approved"]) {
    assert.equal(
      getStageRoute(12, { number: 3, status }),
      "#/pilots/12/stages/3",
    );
  }
});

test("locked and invalid Stage cards do not expose a navigation route", () => {
  assert.equal(getStageRoute(12, { number: 3, status: "locked" }), null);
  assert.equal(getStageRoute(12, { number: 20, status: "open" }), null);
});
