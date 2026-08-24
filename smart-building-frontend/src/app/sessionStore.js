const ACCESS_TOKEN_KEY = "bambo_access_token";
const REFRESH_TOKEN_KEY = "bambo_refresh_token";
const ACCESS_EXPIRES_AT_KEY = "bambo_access_expires_at";
const REFRESH_EXPIRES_AT_KEY = "bambo_refresh_expires_at";
const USER_KEY = "bambo_user_summary";
const REFRESH_LEEWAY_MS = 60_000;

const storage = () => globalThis.window?.sessionStorage ?? null;

const expiresAt = (seconds) => {
  const ttl = Number(seconds);
  return Number.isFinite(ttl) && ttl > 0 ? Date.now() + ttl * 1000 : null;
};

const storedNumber = (key) => {
  const value = Number(storage()?.getItem(key));
  return Number.isFinite(value) && value > 0 ? value : null;
};

const storedUser = () => {
  const target = storage();
  if (!target) return null;
  try {
    return JSON.parse(target.getItem(USER_KEY) ?? "null");
  } catch {
    target.removeItem(USER_KEY);
    return null;
  }
};

let currentUser = null;

const storeOptional = (key, value) => {
  const target = storage();
  if (!target) return;
  if (value === null || value === undefined || value === "") {
    target.removeItem(key);
    return;
  }
  target.setItem(key, String(value));
};

export const sessionStore = Object.freeze({
  getToken: () => storage()?.getItem(ACCESS_TOKEN_KEY) ?? null,
  getRefreshToken: () => storage()?.getItem(REFRESH_TOKEN_KEY) ?? null,
  hasSession: () => Boolean(
    storage()?.getItem(ACCESS_TOKEN_KEY) || storage()?.getItem(REFRESH_TOKEN_KEY),
  ),
  shouldRefreshAccessToken: (leewayMs = REFRESH_LEEWAY_MS) => {
    const refreshToken = storage()?.getItem(REFRESH_TOKEN_KEY);
    if (!refreshToken) return false;

    const refreshExpiry = storedNumber(REFRESH_EXPIRES_AT_KEY);
    if (refreshExpiry && refreshExpiry <= Date.now()) return true;

    const accessToken = storage()?.getItem(ACCESS_TOKEN_KEY);
    const accessExpiry = storedNumber(ACCESS_EXPIRES_AT_KEY);
    return !accessToken || !accessExpiry || accessExpiry <= Date.now() + leewayMs;
  },
  setSession: ({
    accessToken,
    refreshToken,
    expiresIn,
    refreshExpiresIn,
    user,
  }) => {
    storeOptional(ACCESS_TOKEN_KEY, accessToken);
    storeOptional(REFRESH_TOKEN_KEY, refreshToken);
    storeOptional(ACCESS_EXPIRES_AT_KEY, expiresAt(expiresIn));
    storeOptional(REFRESH_EXPIRES_AT_KEY, expiresAt(refreshExpiresIn));
    currentUser = user;
    storeOptional(USER_KEY, user ? JSON.stringify(user) : null);
  },
  setCurrentUser: (user) => {
    currentUser = user;
    storeOptional(USER_KEY, user ? JSON.stringify(user) : null);
  },
  getCurrentUser: () => currentUser ?? storedUser(),
  clear: () => {
    const target = storage();
    target?.removeItem(ACCESS_TOKEN_KEY);
    target?.removeItem(REFRESH_TOKEN_KEY);
    target?.removeItem(ACCESS_EXPIRES_AT_KEY);
    target?.removeItem(REFRESH_EXPIRES_AT_KEY);
    target?.removeItem(USER_KEY);
    currentUser = null;
  },
});

