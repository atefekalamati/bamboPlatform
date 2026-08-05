import assert from "node:assert/strict";
import test from "node:test";

import { matchesUserStatus } from "../src/features/users/userFilters.js";

const activeUser = { isActive: true };
const inactiveUser = { isActive: false };

test("all user filter includes active and inactive users", () => {
  assert.equal(matchesUserStatus(activeUser, "all"), true);
  assert.equal(matchesUserStatus(inactiveUser, "all"), true);
});

test("active user filter only includes active users", () => {
  assert.equal(matchesUserStatus(activeUser, "active"), true);
  assert.equal(matchesUserStatus(inactiveUser, "active"), false);
});

test("inactive user filter only includes inactive users", () => {
  assert.equal(matchesUserStatus(activeUser, "inactive"), false);
  assert.equal(matchesUserStatus(inactiveUser, "inactive"), true);
});

