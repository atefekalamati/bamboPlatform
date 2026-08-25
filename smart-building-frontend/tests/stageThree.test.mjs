import assert from "node:assert/strict";
import test from "node:test";
import {
  buildFloorSlots,
  floorCreationPayload,
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
