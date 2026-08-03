const DEFAULT_REQUEST_TIMEOUT_MS = 30_000;
const runtimeConfig = globalThis.window?.__APP_CONFIG__ ?? globalThis.__APP_CONFIG__ ?? {};
const environment = runtimeConfig.environment ?? "production";

export const APP_CONFIG = Object.freeze({
  name: "BAMBO Pilot",
  locale: "fa-IR",
  direction: "rtl",
  apiBaseUrl: String(runtimeConfig.apiBaseUrl ?? "/backend").replace(/\/$/, ""),
  requestTimeoutMs: Number(runtimeConfig.requestTimeoutMs) || DEFAULT_REQUEST_TIMEOUT_MS,
  environment,
  release: String(runtimeConfig.release ?? "unknown"),
  useMockApi: false,
  isProduction: environment === "production",
});
