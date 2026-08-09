import assert from "node:assert/strict";
import test from "node:test";
import { classifyStageAction } from "../src/app/stageActionLayout.js";

test("stage actions follow the shared save, submit, approve, next and reject order", () => {
  assert.equal(classifyStageAction("ذخیره پیش‌نویس").rank, 10);
  assert.equal(classifyStageAction("ارسال Stage 12 برای بررسی").rank, 20);
  assert.equal(classifyStageAction("تأیید مرحله").rank, 30);
  assert.equal(classifyStageAction("ورود به Stage 13").rank, 40);
  assert.equal(classifyStageAction("رد و درخواست اصلاح").rank, 50);
});

test("unrelated controls are not treated as workflow actions", () => {
  assert.equal(classifyStageAction("افزودن طبقه"), null);
  assert.equal(classifyStageAction("دانلود"), null);
});
