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
  const roles = [{ name: "operations" }];
  assert.equal(canManageMissionAssignments(permissions, roles), true);
  assert.equal(
    canAcceptMissionAssignment({
      currentUserId: 1,
      expertUserId: 15,
      permissions,
      roles,
    }),
    true,
  );
});

test("capture expert never requests the coordinator-only expert directory", () => {
  const permissions = ["missions.manage", "missions.assign"];
  const roles = [{ name: "capture_expert" }];

  assert.equal(canManageMissionAssignments(permissions, roles), false);
  assert.equal(
    canAcceptMissionAssignment({
      currentUserId: 15,
      expertUserId: 15,
      permissions,
      roles,
    }),
    true,
  );
});

test("operations user with an additional capture role remains a coordinator", () => {
  const permissions = ["missions.manage", "missions.assign"];
  const roles = [{ name: "capture_expert" }, { name: "operations" }];

  assert.equal(canManageMissionAssignments(permissions, roles), true);
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

