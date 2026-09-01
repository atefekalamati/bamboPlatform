import assert from "node:assert/strict";
import test from "node:test";

// Two independent stores, mirroring what a browser actually does:
// sessionStorage is dropped when the last tab closes, localStorage survives.
const local = new Map();
const session = new Map();

const asStorage = (map) => ({
  getItem: (key) => map.get(key) ?? null,
  setItem: (key, value) => map.set(key, value),
  removeItem: (key) => map.delete(key),
});

globalThis.window = {
  localStorage: asStorage(local),
  sessionStorage: asStorage(session),
};

const { sessionStore } = await import("../src/app/sessionStore.js");

const closeAndReopenBrowser = () => {
  // The tab goes away; sessionStorage goes with it. localStorage does not.
  session.clear();
};

const signIn = () =>
  sessionStore.setSession({
    accessToken: "access-token",
    refreshToken: "refresh-token",
    expiresIn: 900,
    refreshExpiresIn: 2_592_000,
    user: { id: 7, display_name: "کاربر پایلوت" },
  });

test.beforeEach(() => {
  local.clear();
  session.clear();
  sessionStore.clear();
});

test("the session survives closing and reopening the browser", () => {
  signIn();
  assert.equal(sessionStore.hasSession(), true);

  closeAndReopenBrowser();

  assert.equal(
    sessionStore.hasSession(),
    true,
    "reopening the browser must not sign the user out",
  );
  assert.equal(sessionStore.getRefreshToken(), "refresh-token");
});

test("the reopened tab can still identify the user without a round trip", () => {
  signIn();
  closeAndReopenBrowser();

  const user = sessionStore.getCurrentUser();
  assert.equal(user?.id, 7);
  assert.equal(user?.display_name, "کاربر پایلوت");
});

test("a reopened tab reuses a still-valid access token instead of refreshing", () => {
  signIn();
  closeAndReopenBrowser();

  assert.equal(
    sessionStore.shouldRefreshAccessToken(),
    false,
    "a token with minutes left does not need renewing just because a tab reopened",
  );
});

test("a reopened tab renews an access token that expired while away", () => {
  sessionStore.setSession({
    accessToken: "access-token",
    refreshToken: "refresh-token",
    expiresIn: 1, // one second, gone by the time the browser reopens
    refreshExpiresIn: 2_592_000,
    user: { id: 7 },
  });
  closeAndReopenBrowser();

  assert.equal(
    sessionStore.shouldRefreshAccessToken(),
    true,
    "an expired access token must be renewed before the first protected call",
  );
});

test("without a refresh token there is nothing to renew", () => {
  sessionStore.setSession({
    accessToken: "access-token",
    refreshToken: null,
    expiresIn: 1,
    refreshExpiresIn: null,
    user: { id: 7 },
  });

  assert.equal(sessionStore.shouldRefreshAccessToken(), false);
});

test("signing out clears everything, including what survived the reopen", () => {
  signIn();
  closeAndReopenBrowser();

  sessionStore.clear();

  assert.equal(sessionStore.hasSession(), false);
  assert.equal(sessionStore.getToken(), null);
  assert.equal(sessionStore.getRefreshToken(), null);
  assert.equal(sessionStore.getCurrentUser(), null);
  assert.equal(local.size, 0, "no auth key may be left behind after logout");
});

test("a second tab sees the session the first tab established", () => {
  signIn();
  // A new tab starts with its own empty sessionStorage but shares localStorage.
  session.clear();

  assert.equal(sessionStore.hasSession(), true);
  assert.equal(sessionStore.getRefreshToken(), "refresh-token");
});

test("the refresh path holds a browser-wide lock, not just a per-page guard", async () => {
  const { readFile } = await import("node:fs/promises");
  const client = await readFile(new URL("../src/services/httpClient.js", import.meta.url), "utf8");

  // Tabs share the refresh token now, and the backend revokes every session
  // when a rotated token is replayed, so the guard has to span tabs.
  assert.match(client, /navigator\?\.locks/);
  assert.match(client, /locks\.request\(REFRESH_LOCK/);
  assert.match(client, /withRefreshLock\(async/);
  // And it must notice a refresh that happened while it waited for the lock.
  assert.match(client, /current !== tokenBeforeLock/);
});

test("session state is read from localStorage, never sessionStorage", async () => {
  const { readFile } = await import("node:fs/promises");
  const store = await readFile(new URL("../src/app/sessionStore.js", import.meta.url), "utf8");
  // Strip comments: the rationale for the change names sessionStorage on purpose.
  const code = store.replace(/\/\/[^\n]*/g, "").replace(/\/\*[\s\S]*?\*\//g, "");
  assert.match(code, /window\?\.localStorage/);
  assert.doesNotMatch(code, /sessionStorage/);
});
