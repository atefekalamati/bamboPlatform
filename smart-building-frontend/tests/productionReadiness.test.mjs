import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";
import { canAccessRoute, requiredPermissionForRoute } from "../src/app/routePermissions.js";

test("production config cannot enable mock", async () => {
  const source = await readFile(new URL("../src/config/appConfig.js", import.meta.url), "utf8");
  assert.doesNotMatch(source, /useMockApi\s*:\s*true/);
  assert.doesNotMatch(source, /127\.0\.0\.1|localhost/);
});

test("sensitive routes require backend permissions", () => {
  assert.equal(requiredPermissionForRoute("#/users"), "users.read");
  assert.equal(requiredPermissionForRoute("#/pilots/2/stages/9"), "pilots.read");
  assert.equal(canAccessRoute("#/roles", []), false);
  assert.equal(canAccessRoute("#/roles", ["roles.read"]), true);
});

test("production index has no inline script", async () => {
  const html = await readFile(new URL("../index.html", import.meta.url), "utf8");
  assert.doesNotMatch(html, /<script(?![^>]*\bsrc=)[^>]*>/i);
  assert.match(html, /runtime-config\.js/);
});

test("sensitive stage actions are not gated by role names", async () => {
  for (const page of ["StageFivePage.js", "StageFourteenPage.js", "StageNineteenPage.js"]) {
    const source = await readFile(new URL(`../src/pages/${page}`, import.meta.url), "utf8");
    assert.doesNotMatch(source, /roleNames|super_admin/);
  }
});
