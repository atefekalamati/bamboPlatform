import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";

const source = (relativePath) =>
  readFile(new URL(`../${relativePath}`, import.meta.url), "utf8");

test("notification polling is cancellable and reuses the inbox unread count", async () => {
  const store = await source("src/app/notificationStore.js");
  assert.match(store, /syncController\?\.abort\(\)/);
  assert.match(store, /unreadCount: list\.unread_count/);
  assert.doesNotMatch(store, /notificationService\.getUnreadCount\(\)/);
  assert.match(store, /document\.hidden/);
});

test("router loads page modules on demand", async () => {
  const router = await source("src/app/router.js");
  assert.match(router, /await import\(path\)/);
  assert.doesNotMatch(router, /^import .*\.\.\/pages\//m);
  assert.match(router, /STAGE_LOADERS/);
});

test("Stage 3 consumes DWG versions embedded in the floor response", async () => {
  const page = await source("src/pages/StageThreePage.js");
  const service = await source("src/services/dwgService.js");
  assert.match(page, /floor\.dwgVersions/);
  assert.doesNotMatch(page, /floors\.map\(\(floor\) => dwgService\.getVersions/);
  assert.match(service, /floor\.dwg_versions/);
});

test("management lists use versioned server pagination", async () => {
  const usersPage = await source("src/pages/UsersPage.js");
  const pilotsPage = await source("src/pages/PilotsPage.js");
  const usersService = await source("src/services/userService.js");
  const pilotsService = await source("src/services/pilotService.js");
  assert.match(usersPage, /getUsersPage/);
  assert.match(pilotsPage, /getPilotsPage/);
  assert.match(usersPage, /currentPage = result\.page;\s*render\(\);/);
  assert.doesNotMatch(usersPage, /currentPage = result\.page;\s*loadUsers\(\);/);
  assert.match(usersService, /API_BASE_PATHS\.users/);
  assert.match(pilotsService, /API_BASE_PATHS\.pilots/);
});
