import assert from "node:assert/strict";
import test from "node:test";

const local = new Map();
const session = new Map();
const attributes = new Map();

globalThis.window = {
  localStorage: {
    getItem: (key) => local.get(key) ?? null,
    setItem: (key, value) => local.set(key, String(value)),
    // sessionStore keeps the auth session here too, and clearing it removes keys.
    removeItem: (key) => local.delete(key),
  },
  sessionStorage: {
    getItem: (key) => session.get(key) ?? null,
    setItem: (key, value) => session.set(key, String(value)),
    removeItem: (key) => session.delete(key),
  },
  matchMedia: () => ({ matches: false }),
};
globalThis.document = {
  documentElement: {
    setAttribute: (key, value) => attributes.set(key, value),
    getAttribute: (key) => attributes.get(key) ?? null,
  },
};

const { sessionStore } = await import("../src/app/sessionStore.js");
const { themeStore } = await import("../src/app/themeStore.js");

test.beforeEach(() => {
  local.clear();
  session.clear();
  attributes.clear();
  sessionStore.clear();
});

test("stores separate themes for each authenticated user", () => {
  sessionStore.setCurrentUser({ id: 7 });
  themeStore.setTheme("dark");
  sessionStore.setCurrentUser({ id: 8 });
  themeStore.setTheme("light");
  assert.equal(local.get("bambo_theme:user:7"), "dark");
  assert.equal(local.get("bambo_theme:user:8"), "light");
  assert.equal(themeStore.init(7), "dark");
});

test("local user choice wins over a stale server preference", () => {
  local.set("bambo_theme:user:7", "dark");
  themeStore.syncFromServer("light", 7);
  assert.equal(attributes.get("data-theme"), "dark");
});
