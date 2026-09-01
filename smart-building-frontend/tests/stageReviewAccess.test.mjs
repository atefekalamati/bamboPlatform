import assert from "node:assert/strict";
import test from "node:test";
import { readFile } from "node:fs/promises";

import { getStageReviewAccess } from "../src/features/stages/stageReviewAccess.js";

const reviewer = (stageAccess, permissions = [
  "gate_approval.approve",
  "gate_approval.reject",
]) => ({ permissions, stageAccess });

test("shows review actions only for stages explicitly granted by backend", () => {
  const user = reviewer({ approve: [4, 5], reject: [4] });
  assert.deepEqual(getStageReviewAccess(user, 4), {
    canApprove: true,
    canReject: true,
  });
  assert.deepEqual(getStageReviewAccess(user, 5), {
    canApprove: true,
    canReject: false,
  });
  assert.deepEqual(getStageReviewAccess(user, 6), {
    canApprove: false,
    canReject: false,
  });
});

test("a broad permission alone never exposes another stage review panel", () => {
  const user = reviewer({ approve: [], reject: [] });
  assert.deepEqual(getStageReviewAccess(user, 9), {
    canApprove: false,
    canReject: false,
  });
});

test("authentication loads authoritative stage access from backend bootstrap", async () => {
  const source = await readFile(new URL("../src/services/authService.js", import.meta.url), "utf8");
  assert.match(source, /request\("\/auth\/bootstrap"\)/);
  assert.match(source, /stageAccess:\s*payload\.stage_access/);
});

test("all shared review panels enforce stage-level access", async () => {
  const source = await readFile(new URL("../src/components/StageShared.js", import.meta.url), "utf8");
  assert.match(source, /getStageReviewAccess/);
  assert.match(source, /if \(!allowApprove && !allowReject\) return document\.createDocumentFragment\(\)/);
});
