/**
 * API routing contract.
 *
 * Legacy endpoints intentionally have no application-level prefix. The reverse
 * proxy origin/base (for example `/backend`) belongs to APP_CONFIG.apiBaseUrl
 * and is added by httpClient. New versioned backend routers live under
 * `/api/v1`; do not prepend that prefix to legacy paths unless Backend changes
 * its explicit contract.
 */
export const API_PREFIXES = Object.freeze({
  legacy: "",
  v1: "/api/v1",
});

export const API_BASE_PATHS = Object.freeze({
  dashboard: `${API_PREFIXES.v1}/dashboard`,
  reports: `${API_PREFIXES.v1}/reports`,
  users: `${API_PREFIXES.v1}/users`,
  pilots: `${API_PREFIXES.v1}/pilots`,
});
