import assert from "node:assert/strict";
import test from "node:test";
import { matchStageRoute, normalizeRoutePath } from "../src/app/routeMatcher.js";

test("normalizes query parameters before route matching", () => {
  assert.equal(normalizeRoutePath("#/pilots/2/stages/9?source=dashboard"), "#/pilots/2/stages/9");
});

test("matches every official stage with or without query parameters", () => {
  for (let stageNumber = 1; stageNumber <= 19; stageNumber += 1) {
    assert.deepEqual(matchStageRoute(`#/pilots/pilot-005/stages/${stageNumber}?source=test`), {
      pilotId: "pilot-005",
      stageNumber,
    });
  }
});

test("rejects invalid stage routes", () => {
  assert.equal(matchStageRoute("#/pilots/2/stages/0"), null);
  assert.equal(matchStageRoute("#/pilots/2/stages/20"), null);
  assert.equal(matchStageRoute("#/pilots/2/stages/not-a-stage"), null);
});
