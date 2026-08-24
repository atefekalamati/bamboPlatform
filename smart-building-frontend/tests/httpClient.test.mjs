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
const { authService } = await import("../src/services/authService.js");

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

test("stores rotating refresh session returned by a successful login", async () => {
  globalThis.fetch = async (url) => {
    assert.match(String(url), /\/auth\/otp\/verify$/);
    return new Response(
      JSON.stringify({
        access_token: "access-login",
        refresh_token: "refresh-login",
        expires_in: 900,
        refresh_expires_in: 2_592_000,
        user: { id: 7, display_name: "کاربر تست" },
      }),
      { status: 200, headers: { "content-type": "application/json" } },
    );
  };

  await authService.verifyOtp({
    requestId: "00000000-0000-0000-0000-000000000000",
    code: "123456",
  });

  assert.equal(storage.get("bambo_access_token"), "access-login");
  assert.equal(storage.get("bambo_refresh_token"), "refresh-login");
  assert.ok(Number(storage.get("bambo_access_expires_at")) > Date.now());
  assert.ok(Number(storage.get("bambo_refresh_expires_at")) > Date.now());
});

test("refreshes a near-expiry access token before the protected request", async () => {
  storage.set("bambo_access_token", "access-old");
  storage.set("bambo_refresh_token", "refresh-old");
  storage.set("bambo_access_expires_at", String(Date.now() + 1_000));
  storage.set("bambo_refresh_expires_at", String(Date.now() + 60_000));
  const calls = [];

  globalThis.fetch = async (url, options) => {
    calls.push({ url: String(url), options });
    if (String(url).endsWith("/auth/refresh")) {
      return new Response(
        JSON.stringify({
          access_token: "access-new",
          refresh_token: "refresh-new",
          expires_in: 900,
          refresh_expires_in: 2_592_000,
          user: { id: 1 },
        }),
        { status: 200, headers: { "content-type": "application/json" } },
      );
    }
    return new Response(JSON.stringify({ id: 1 }), {
      status: 200,
      headers: { "content-type": "application/json" },
    });
  };

  await request("/auth/me");

  assert.equal(calls.length, 2);
  assert.match(calls[0].url, /\/auth\/refresh$/);
  assert.equal(calls[0].options.headers.Authorization, undefined);
  assert.equal(calls[1].options.headers.Authorization, "Bearer access-new");
  assert.equal(storage.get("bambo_refresh_token"), "refresh-new");
});

test("retries a 401 once after refresh and keeps the user signed in", async () => {
  storage.set("bambo_access_token", "access-expired");
  storage.set("bambo_refresh_token", "refresh-old");
  storage.set("bambo_access_expires_at", String(Date.now() + 120_000));
  let protectedCalls = 0;
  let refreshCalls = 0;

  globalThis.fetch = async (url, options) => {
    if (String(url).endsWith("/auth/refresh")) {
      refreshCalls += 1;
      return new Response(
        JSON.stringify({
          access_token: "access-rotated",
          refresh_token: "refresh-rotated",
          expires_in: 900,
          refresh_expires_in: 2_592_000,
          user: { id: 1 },
        }),
        { status: 200, headers: { "content-type": "application/json" } },
      );
    }
    protectedCalls += 1;
    return options.headers.Authorization === "Bearer access-rotated"
      ? new Response(JSON.stringify({ ok: true }), {
          status: 200,
          headers: { "content-type": "application/json" },
        })
      : new Response(JSON.stringify({ code: "SESSION_EXPIRED" }), {
          status: 401,
          headers: { "content-type": "application/json" },
        });
  };

  assert.deepEqual(await request("/pilots"), { ok: true });
  assert.equal(refreshCalls, 1);
  assert.equal(protectedCalls, 2);
  assert.equal(events.some(({ type }) => type === "bambo:auth-required"), false);
});

test("coalesces simultaneous 401 responses into one rotating refresh", async () => {
  storage.set("bambo_access_token", "access-expired");
  storage.set("bambo_refresh_token", "refresh-old");
  storage.set("bambo_access_expires_at", String(Date.now() + 120_000));
  let refreshCalls = 0;

  globalThis.fetch = async (url, options) => {
    if (String(url).endsWith("/auth/refresh")) {
      refreshCalls += 1;
      await new Promise((resolve) => setTimeout(resolve, 10));
      return new Response(
        JSON.stringify({
          access_token: "access-shared",
          refresh_token: "refresh-shared",
          expires_in: 900,
          refresh_expires_in: 2_592_000,
          user: { id: 1 },
        }),
        { status: 200, headers: { "content-type": "application/json" } },
      );
    }
    return options.headers.Authorization === "Bearer access-shared"
      ? new Response(JSON.stringify({ ok: true }), {
          status: 200,
          headers: { "content-type": "application/json" },
        })
      : new Response(JSON.stringify({ code: "SESSION_EXPIRED" }), {
          status: 401,
          headers: { "content-type": "application/json" },
        });
  };

  const results = await Promise.all([
    request("/pilots"),
    request("/notifications"),
    request("/api/v1/dashboard/summary"),
  ]);

  assert.equal(refreshCalls, 1);
  assert.deepEqual(results, [{ ok: true }, { ok: true }, { ok: true }]);
});

test("clears the whole session when refresh token is rejected", async () => {
  storage.set("bambo_access_token", "access-expired");
  storage.set("bambo_refresh_token", "refresh-broken");
  storage.set("bambo_access_expires_at", String(Date.now() + 120_000));

  globalThis.fetch = async (url) =>
    String(url).endsWith("/auth/refresh")
      ? new Response(JSON.stringify({ code: "REFRESH_INVALID" }), {
          status: 401,
          headers: { "content-type": "application/json" },
        })
      : new Response(JSON.stringify({ code: "SESSION_EXPIRED" }), {
          status: 401,
          headers: { "content-type": "application/json" },
        });

  await assert.rejects(request("/auth/me"), (error) => error.status === 401);
  assert.equal(storage.has("bambo_access_token"), false);
  assert.equal(storage.has("bambo_refresh_token"), false);
  assert.equal(
    events.filter(({ type }) => type === "bambo:auth-required").length,
    1,
  );
});

test("logout sends the refresh token for server-side revocation and clears storage", async () => {
  storage.set("bambo_access_token", "access-active");
  storage.set("bambo_refresh_token", "refresh-active");
  storage.set("bambo_access_expires_at", String(Date.now() + 120_000));
  let logoutBody = null;
  globalThis.fetch = async (url, options) => {
    assert.match(String(url), /\/auth\/logout$/);
    logoutBody = JSON.parse(options.body);
    return new Response(null, { status: 204 });
  };

  await authService.logout();

  assert.deepEqual(logoutBody, { refresh_token: "refresh-active" });
  assert.equal(storage.size, 0);
});

test("does not enter a refresh loop when the retried request is still unauthorized", async () => {
  storage.set("bambo_access_token", "access-old");
  storage.set("bambo_refresh_token", "refresh-old");
  storage.set("bambo_access_expires_at", String(Date.now() + 120_000));
  let refreshCalls = 0;
  let protectedCalls = 0;
  globalThis.fetch = async (url) => {
    if (String(url).endsWith("/auth/refresh")) {
      refreshCalls += 1;
      return new Response(
        JSON.stringify({
          access_token: "access-new",
          refresh_token: "refresh-new",
          expires_in: 900,
          refresh_expires_in: 2_592_000,
          user: { id: 1 },
        }),
        { status: 200, headers: { "content-type": "application/json" } },
      );
    }
    protectedCalls += 1;
    return new Response(JSON.stringify({ code: "SESSION_INVALID" }), {
      status: 401,
      headers: { "content-type": "application/json" },
    });
  };

  await assert.rejects(request("/pilots"), (error) => error.status === 401);
  assert.equal(refreshCalls, 1);
  assert.equal(protectedCalls, 2);
  assert.equal(storage.size, 0);
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
