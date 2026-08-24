import assert from "node:assert/strict";
import test from "node:test";
import { STAGE_ONE_FIXED_CONTROLS } from "../src/features/stages/stageOne.js";

test("Stage 1 additional controls are always accepted", () => {
  assert.deepEqual(STAGE_ONE_FIXED_CONTROLS, {
    imagingValue: true,
    notDemoOnly: true,
  });
});
