import assert from "node:assert/strict";
import test from "node:test";
import {
  buildFloorSlots,
  floorCreationPayload,
  getFloorRegistrationState,
  runFloorBulkOperation,
} from "../src/features/stages/stageThree.js";

test("prepares one stable Stage 3 card for every project floor", () => {
  const floors = [{ code: "F02", levelOrder: 1, name: "دوم" }];
  const slots = buildFloorSlots(3, floors);
  assert.equal(slots.length, 3);
  assert.deepEqual(slots.map(({ code }) => code), ["F01", "F02", "F03"]);
  assert.equal(slots[1].floor, floors[0]);
  assert.equal(slots[0].floor, null);
});

test("keeps a formerly custom-coded floor without creating an extra card", () => {
  const customFloor = { code: "F10", levelOrder: 9, name: "بام" };
  const slots = buildFloorSlots(1, [customFloor]);
  assert.equal(slots.length, 1);
  assert.equal(slots[0].floor, customFloor);
});

test("creates the backend floor payload from a rendered card", () => {
  assert.deepEqual(
    floorCreationPayload(
      { code: "F01", levelOrder: 0 },
      "  همکف  ",
      "typical",
    ),
    { code: "F01", name: "همکف", levelOrder: 0, floorType: "typical" },
  );
});

test("keeps Stage 3 submission locked until every project floor is persisted", () => {
  assert.deepEqual(getFloorRegistrationState(3, [
    { id: 11, code: "F01", levelOrder: 0, name: "همکف" },
    { id: 12, code: "F02", levelOrder: 1, name: "اول" },
  ]), {
    totalCount: 3,
    registeredCount: 2,
    missingCount: 1,
    isComplete: false,
  });
});

test("unlocks Stage 3 submission after every floor is persisted with a name", () => {
  const state = getFloorRegistrationState(2, [
    { id: 11, code: "F01", levelOrder: 0, name: "همکف" },
    { id: 12, code: "F02", levelOrder: 1, name: "اول" },
  ]);

  assert.equal(state.isComplete, true);
  assert.equal(state.missingCount, 0);
});

test("does not count an unsaved or unnamed floor as registered", () => {
  const state = getFloorRegistrationState(2, [
    { code: "F01", levelOrder: 0, name: "همکف" },
    { id: 12, code: "F02", levelOrder: 1, name: "  " },
  ]);

  assert.equal(state.registeredCount, 0);
  assert.equal(state.isComplete, false);
});

test("Stage 3 uses integrated floor evidence cards without a separate registration action", async () => {
  const source = await import("node:fs/promises").then(({ readFile }) =>
    readFile(new URL("../src/pages/StageThreePage.js", import.meta.url), "utf8"),
  );

  assert.doesNotMatch(source, /ثبت اطلاعات طبقات/);
  assert.match(source, /انتخاب فایل و ثبت طبقه/);
  assert.match(source, /typical\.type = nonTypical\.type = "radio"/);
  assert.match(source, /file\.addEventListener\("change"/);
  assert.match(source, /نقشه در اختیار من نیست/);
  assert.match(source, /submit\.disabled = !complete/);
});

test("Stage 3 floor cards use a responsive three-column desktop grid", async () => {
  const styles = await import("node:fs/promises").then(({ readFile }) =>
    readFile(new URL("../src/styles/stage-workspace.css", import.meta.url), "utf8"),
  );

  assert.match(
    styles,
    /\.floor-definition\s*\{[^}]*grid-template-columns:\s*repeat\(3,\s*minmax\(0,\s*1fr\)\)/s,
  );
  assert.match(styles, /@media \(max-width: 36rem\)[\s\S]*?\.floor-definition\s*\{\s*grid-template-columns:\s*1fr/);
});

test("Stage 3 keeps completed cards compact before submission", async () => {
  const { readFile } = await import("node:fs/promises");
  const source = await readFile(
    new URL("../src/pages/StageThreePage.js", import.meta.url),
    "utf8",
  );
  const styles = await readFile(
    new URL("../src/styles/stage-workspace.css", import.meta.url),
    "utf8",
  );

  assert.doesNotMatch(source, /هنوز طبقه‌ای ثبت نشده است/);
  assert.match(source, /completedFloorCard/);
  assert.match(source, /\["open", "needs_revision"\]\.includes\(stage\.status\)/);
  assert.match(styles, /\.floor-card--completed\s*\{[^}]*overflow:\s*hidden/s);
  assert.match(styles, /\.floor-card__filename\s*\{[^}]*text-overflow:\s*ellipsis/s);
  assert.match(styles, /\.floor-card__radio:hover:not\(:has\(input:disabled\)\)/);
});

test("runs a bulk floor operation sequentially and reports partial failures", async () => {
  const progress = [];
  const result = await runFloorBulkOperation(
    [{ id: 1 }, { id: 2 }, { id: 3 }],
    async ({ id }) => {
      if (id === 2) throw new Error("failed");
    },
    (state) => progress.push(state),
  );

  assert.deepEqual(result.succeeded.map(({ id }) => id), [1, 3]);
  assert.deepEqual(result.failed.map(({ item }) => item.id), [2]);
  assert.deepEqual(progress.at(-1), {
    completed: 3,
    total: 3,
    succeeded: 2,
    failed: 1,
  });
});

test("Stage 3 provides bulk map actions without removing per-floor actions", async () => {
  const source = await import("node:fs/promises").then(({ readFile }) =>
    readFile(new URL("../src/pages/StageThreePage.js", import.meta.url), "utf8"),
  );

  assert.match(source, /نقشه در اختیار نیست برای همه/);
  assert.match(source, /انتخاب یک DWG برای همه/);
  assert.match(source, /انتخاب فایل و ثبت طبقه/);
  assert.match(source, /runFloorBulkOperation/);
});

test("Stage 3 identifies floor cards only with compact F-number labels", async () => {
  const source = await import("node:fs/promises").then(({ readFile }) =>
    readFile(new URL("../src/pages/StageThreePage.js", import.meta.url), "utf8"),
  );

  assert.match(source, /floor-card__index-label/);
  assert.match(source, /`F-\$\{slot\.index\}`/);
  assert.match(source, /`F-\$\{floor\.levelOrder \+ 1\}`/);
  assert.doesNotMatch(source, /`نام طبقه \$\{slot\.index\}`/);
  assert.doesNotMatch(source, /"تکمیل‌نشده"/);
  assert.doesNotMatch(source, /"ثبت‌شده"/);
});
