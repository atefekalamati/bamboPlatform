import assert from "node:assert/strict";
import test from "node:test";

const storage = new Map();
globalThis.window = {
  sessionStorage: {
    getItem: (key) => storage.get(key) ?? null,
    setItem: (key, value) => storage.set(key, value),
    removeItem: (key) => storage.delete(key),
  },
};

const { sessionStore } = await import("../src/app/sessionStore.js");

test.beforeEach(() => {
  storage.clear();
  sessionStore.clear();
});

test("persists only authentication metadata and user summary for browser reload", () => {
  sessionStore.setSession({
    accessToken: "access-token",
    refreshToken: "refresh-token",
    expiresIn: 900,
    refreshExpiresIn: 2_592_000,
    user: { id: 12, display_name: "کاربر پایلوت" },
  });

  assert.equal(sessionStore.hasSession(), true);
  assert.equal(sessionStore.getToken(), "access-token");
  assert.equal(sessionStore.getRefreshToken(), "refresh-token");
  assert.equal(storage.size, 5);
  assert.equal(JSON.parse(storage.get("bambo_user_summary")).id, 12);
});

test("recognizes an access token close to expiry", () => {
  sessionStore.setSession({
    accessToken: "short-access",
    refreshToken: "long-refresh",
    expiresIn: 1,
    refreshExpiresIn: 3_600,
    user: { id: 1 },
  });

  assert.equal(sessionStore.shouldRefreshAccessToken(), true);
});

test("clear removes access, refresh, expiry and user metadata", () => {
  sessionStore.setSession({
    accessToken: "access-token",
    refreshToken: "refresh-token",
    expiresIn: 900,
    refreshExpiresIn: 3_600,
    user: { id: 1 },
  });

  sessionStore.clear();

  assert.equal(storage.size, 0);
  assert.equal(sessionStore.getCurrentUser(), null);
});
