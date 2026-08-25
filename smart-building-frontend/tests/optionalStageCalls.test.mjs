import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";

const OPTIONAL_CALL_STAGES = Object.freeze([
  ["StageTwoPage.js", 2],
  ["StageFivePage.js", 5],
  ["StageElevenPage.js", 11],
  ["StageThirteenPage.js", 13],
  ["StageSixteenPage.js", 16],
]);

test("all backend-supported optional call stages use the shared CallsPanel", async () => {
  for (const [filename, stageNumber] of OPTIONAL_CALL_STAGES) {
    const source = await readFile(new URL(`../src/pages/${filename}`, import.meta.url), "utf8");
    assert.match(source, /import \{ CallsPanel \}/, `${filename} must import CallsPanel`);
    assert.match(source, new RegExp(`CallsPanel\\(\\{[^}]*stageNumber:\\s*${stageNumber}[^}]*\\}\\)`), `${filename} must bind Stage ${stageNumber}`);
    assert.doesNotMatch(source, new RegExp(`stageNumber:\\s*${stageNumber}[^}]*required:\\s*true`), `${filename} must keep calls optional`);
  }
});
