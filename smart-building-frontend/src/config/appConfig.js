const DEFAULT_REQUEST_TIMEOUT_MS = 30_000;

export const APP_CONFIG = Object.freeze({
  name: "BAMBO Pilot",
  locale: "fa-IR",
  direction: "rtl",
  apiBaseUrl: "/api/v1",
  requestTimeoutMs: DEFAULT_REQUEST_TIMEOUT_MS,
  useMockApi: true,
});
