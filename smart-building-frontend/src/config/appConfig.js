const DEFAULT_REQUEST_TIMEOUT_MS = 30_000;

export const APP_CONFIG = Object.freeze({
  name: "BAMBO Pilot",
  locale: "fa-IR",
  direction: "rtl",
  apiBaseUrl: "http://127.0.0.1:8000",
  requestTimeoutMs: DEFAULT_REQUEST_TIMEOUT_MS,
  useMockApi: true,
});
