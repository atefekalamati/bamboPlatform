import assert from "node:assert/strict";
import test from "node:test";

const storage = new Map();
const events = [];

globalThis.CustomEvent = class CustomEvent {
  constructor(type, options = {}) {
    this.type = type;
    this.detail = options.detail;
  }
};

globalThis.window = {
  clearTimeout,
  setTimeout,
  dispatchEvent: (event) => events.push(event),
  sessionStorage: {
    getItem: (key) => storage.get(key) ?? null,
    setItem: (key, value) => storage.set(key, value),
    removeItem: (key) => storage.delete(key),
  },
};

const { request } = await import("../src/services/httpClient.js");

test.beforeEach(() => {
  storage.clear();
  events.length = 0;
});

test("does not retry a 409 stage conflict", async () => {
  let requestCount = 0;
  globalThis.fetch = async () => {
    requestCount += 1;
    return new Response(
      JSON.stringify({
        code: "STAGE_CONFLICT",
        message: "مرحله قبلاً تغییر کرده است.",
        stage: 9,
        errors: [],
        trace_id: "trace-conflict",
      }),
      { status: 409, headers: { "content-type": "application/json" } },
    );
  };

  await assert.rejects(
    request("/pilots/2/stages/9/submit", { method: "POST" }),
    (error) =>
      error.status === 409 &&
      error.code === "STAGE_CONFLICT" &&
      error.stage === 9,
  );
  assert.equal(requestCount, 1);
});

test("clears an existing session and announces authentication on 401", async () => {
  storage.set("bambo_access_token", "expired-token");
  globalThis.fetch = async () =>
    new Response(
      JSON.stringify({
        code: "SESSION_EXPIRED",
        message: "نشست منقضی شده است.",
        errors: [],
      }),
      { status: 401, headers: { "content-type": "application/json" } },
    );

  await assert.rejects(request("/auth/me"), (error) => error.status === 401);
  assert.equal(storage.has("bambo_access_token"), false);
  assert.ok(events.some(({ type }) => type === "bambo:auth-required"));
});

test("preserves FastAPI field validation metadata", async () => {
  globalThis.fetch = async () =>
    new Response(
      JSON.stringify({
        detail: [
          {
            loc: ["body", "display_name"],
            msg: "Field required",
            type: "missing",
          },
        ],
      }),
      { status: 422, headers: { "content-type": "application/json" } },
    );

  await assert.rejects(
    request("/users", { method: "POST" }),
    (error) =>
      error.status === 422 && error.errors[0]?.field === "display_name",
  );
});
