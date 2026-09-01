import test from "node:test";
import assert from "node:assert/strict";

import { accessDeniedReason, canAccessRoute } from "../src/app/routePermissions.js";
import { ROUTES } from "../src/constants/routes.js";

// A brand-new account signs in with no roles. The backend allows the login and
// refuses every protected call, so the first thing this person sees is a
// refusal page — it has to explain the situation rather than name a permission
// code, and it must not offer a link back to the page that just refused them.

test("a roleless user is told they have no role yet, not a permission code", () => {
  const reason = accessDeniedReason(ROUTES.dashboard, [], []);
  assert.match(reason.title, /نقشی برای حساب شما تعیین نشده/);
  assert.doesNotMatch(reason.message, /dashboard\.read/);
  assert.doesNotMatch(reason.title, /dashboard\.read/);
});

test("a roleless user is not offered a link back to the page that refused them", () => {
  assert.equal(canAccessRoute(ROUTES.dashboard, [], []), false);
  assert.equal(accessDeniedReason(ROUTES.dashboard, [], []).returnRoute, null);
});

test("a user with roles still sees which permission is missing", () => {
  const roles = [{ name: "support" }];
  const permissions = ["dashboard.read"];
  const reason = accessDeniedReason(ROUTES.users, permissions, roles);
  assert.match(reason.title, /دسترسی به این صفحه امکان‌پذیر نیست/);
  assert.match(reason.message, /users\.read/);
});

test("the dashboard link appears only when the dashboard is reachable", () => {
  const roles = [{ name: "support" }];
  const withDashboard = accessDeniedReason(ROUTES.users, ["dashboard.read"], roles);
  assert.equal(withDashboard.returnRoute, ROUTES.dashboard);

  const withoutDashboard = accessDeniedReason(ROUTES.users, ["pilots.read"], roles);
  assert.equal(withoutDashboard.returnRoute, null);
});

test("an unknown route still produces a usable message for a user with roles", () => {
  const reason = accessDeniedReason("#/nowhere", ["dashboard.read"], [{ name: "support" }]);
  assert.match(reason.message, /نامشخص/);
});

test("router renders the reason instead of hardcoding the old message", async () => {
  const { readFile } = await import("node:fs/promises");
  const router = await readFile(new URL("../src/app/router.js", import.meta.url), "utf8");
  assert.match(router, /accessDeniedReason\(route, permissions, roles\)/);
  // The old page always appended a dashboard link; it must now be conditional.
  assert.match(router, /if \(reason\.returnRoute\)/);
});
