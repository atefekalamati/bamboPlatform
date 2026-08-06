import assert from "node:assert/strict";
import test from "node:test";
import { getStageTitle, stageOptions, STAGE_TITLES } from "../src/constants/stageCatalog.js";

test("exposes one official title for every pilot stage", () => {
  assert.equal(Object.keys(STAGE_TITLES).length, 19);
  assert.equal(stageOptions().length, 19);
  assert.equal(getStageTitle(9), "وضعیت Upload در پلتفرم اصلی");
  assert.equal(getStageTitle(19), "تبدیل پایلوت به قرارداد یا بستن پرونده");
});

test("prefers a valid API title and controls invalid stage fallback", () => {
  assert.equal(getStageTitle(3, "عنوان رسمی Backend"), "عنوان رسمی Backend");
  assert.equal(getStageTitle(0), "مرحله نامشخص");
  assert.equal(getStageTitle("unknown"), "مرحله نامشخص");
});
