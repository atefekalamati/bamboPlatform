import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";
import { canAccessRoute, requiredPermissionForRoute } from "../src/app/routePermissions.js";

test("production config cannot enable mock", async () => {
  const source = await readFile(new URL("../src/config/appConfig.js", import.meta.url), "utf8");
  assert.doesNotMatch(source, /useMockApi\s*:\s*true/);
  assert.doesNotMatch(source, /127\.0\.0\.1|localhost/);
});

test("frontend contains no removed backend call integration", async () => {
  const files = [
    "../src/pages/StageTwoPage.js", "../src/pages/StageFivePage.js",
    "../src/pages/StageElevenPage.js", "../src/pages/StageThirteenPage.js",
    "../src/pages/StageSixteenPage.js", "../src/pages/StageEighteenPage.js",
  ];
  for (const file of files) {
    const source = await readFile(new URL(file, import.meta.url), "utf8");
    assert.doesNotMatch(source, /CallsPanel|callService|call_policy_completed/);
    assert.doesNotMatch(source, /calls\.(read|initiate|retry|override|record_outcome)|calls\.recording\.read/);
  }
});

test("Stage 18 contains no legacy call requirement", async () => {
  const source = await readFile(
    new URL("../src/pages/StageEighteenPage.js", import.meta.url),
    "utf8",
  );

  assert.doesNotMatch(source, /تماس|Call|VoIP|Astel/i);
  assert.match(source, /هر پیگیری برای رفع یک مانع مشخص/);
});

test("sensitive routes require backend permissions", () => {
  assert.equal(requiredPermissionForRoute("#/users"), "users.read");
  assert.equal(requiredPermissionForRoute("#/pilots/2/stages/9"), "pilots.read");
  assert.equal(canAccessRoute("#/roles", []), false);
  assert.equal(canAccessRoute("#/roles", ["roles.read"], [{ name: "operations" }]), false);
  assert.equal(canAccessRoute("#/roles", ["roles.read"], [{ name: "admin" }]), true);
  assert.equal(canAccessRoute("#/roles", ["roles.read"], [{ name: "super_admin" }]), true);
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

test("all stage routes install the shared unsaved changes guard", async () => {
  const router = await readFile(new URL("../src/app/router.js", import.meta.url), "utf8");
  const guard = await readFile(new URL("../src/app/navigationGuard.js", import.meta.url), "utf8");
  assert.match(router, /installStageNavigationGuard/);
  assert.match(guard, /pilots.*stages/);
  assert.match(guard, /تغییرات این مرحله هنوز ذخیره نشده است/);
});

test("all stage routes install the shared action layout", async () => {
  const router = await readFile(new URL("../src/app/router.js", import.meta.url), "utf8");
  assert.match(router, /installStageActionLayout/);
});

test("dashboard does not expose the removed Power BI backend contract", async () => {
  const dashboard = await readFile(new URL("../src/pages/DashboardPage.js", import.meta.url), "utf8");
  const service = await readFile(new URL("../src/services/dashboardService.js", import.meta.url), "utf8");
  const nginx = await readFile(new URL("../nginx.conf", import.meta.url), "utf8");
  assert.doesNotMatch(dashboard, /PowerBI|powerbi|reports\.powerbi/i);
  assert.doesNotMatch(service, /getPowerBIEmbed|embed-token/i);
  assert.doesNotMatch(nginx, /powerbi\.com/i);
});

test("unknown routes render a not-found page instead of the dashboard", async () => {
  const router = await readFile(new URL("../src/app/router.js", import.meta.url), "utf8");
  assert.match(router, /page: notFoundPage\(\)/);
  assert.doesNotMatch(router, /return\s*\{\s*page: DashboardPage\(\),\s*navigationRoute: ROUTES\.dashboard/);
});

test("dynamic workflow feedback is exposed as a live region", async () => {
  const bootstrap = await readFile(new URL("../src/app/bootstrap.js", import.meta.url), "utf8");
  const accessibility = await readFile(new URL("../src/app/accessibility.js", import.meta.url), "utf8");
  assert.match(bootstrap, /startLiveRegionEnhancements\(\)/);
  assert.match(accessibility, /\.stage-actions__feedback/);
  assert.match(accessibility, /aria-live/);
});
