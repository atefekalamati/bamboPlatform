import assert from "node:assert/strict";
import test from "node:test";

import {
  canAcceptMissionAssignment,
  canManageMissionAssignments,
} from "../src/features/missions/missionPermissions.js";

test("assigned capture expert can accept their own mission", () => {
  assert.equal(
    canAcceptMissionAssignment({
      currentUserId: 15,
      expertUserId: 15,
      permissions: ["missions.manage"],
    }),
    true,
  );
});

test("mission assignment manager can accept for the assigned expert", () => {
  const permissions = ["missions.manage", "missions.assign"];
  assert.equal(canManageMissionAssignments(permissions), true);
  assert.equal(
    canAcceptMissionAssignment({
      currentUserId: 1,
      expertUserId: 15,
      permissions,
    }),
    true,
  );
});

test("unassigned field expert cannot accept another expert mission", () => {
  assert.equal(
    canAcceptMissionAssignment({
      currentUserId: 16,
      expertUserId: 15,
      permissions: ["missions.manage"],
    }),
    false,
  );
});

