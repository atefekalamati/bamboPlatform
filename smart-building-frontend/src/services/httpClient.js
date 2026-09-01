import { sessionStore } from "../app/sessionStore.js";
import {
  reportApiError,
  reportAuthenticationRequired,
} from "../app/apiErrorPresenter.js";
import { APP_CONFIG } from "../config/appConfig.js";
import {
  ApiError,
  apiErrorFromResponse,
  invalidResponseApiError,
  networkApiError,
  timeoutApiError,
} from "./apiError.js";

const requestUrl = (path) => `${APP_CONFIG.apiBaseUrl}${path}`;
const REFRESH_PATH = "/auth/refresh";
const PUBLIC_AUTH_PATHS = new Set([
  "/auth/otp/request",
  "/auth/otp/verify",
  REFRESH_PATH,
]);
let refreshPromise = null;

const parsePayload = async (response) => {
  const rawBody = await response.text();
  if (!rawBody) return null;

  try {
    return JSON.parse(rawBody);
  } catch (cause) {
    if (response.ok) {
      throw invalidResponseApiError({ status: response.status, cause });
    }
    return null;
  }
};

const parseResponse = async (response) => {
  if (response.status === 204) return null;
  const payload = await parsePayload(response);
  if (response.ok) return payload;

  throw apiErrorFromResponse({ status: response.status, payload });
};

const handleApiError = (error, { hadSession }) => {
  if (!error.authenticationHandled) reportApiError(error);

  if (error.status === 401 && hadSession && !error.authenticationHandled) {
    sessionStore.clear();
    reportAuthenticationRequired(error);
    error.authenticationHandled = true;
  }

  throw error;
};

const executeRequest = async (path, options = {}, { includeAuth = true } = {}) => {
  const controller = new AbortController();
  const externalSignal = options.signal;
  const abortFromCaller = () => controller.abort();
  externalSignal?.addEventListener("abort", abortFromCaller, { once: true });
  let didTimeout = false;
  const timeoutId = window.setTimeout(() => {
    didTimeout = true;
    controller.abort();
  }, APP_CONFIG.requestTimeoutMs);
  const token = includeAuth ? sessionStore.getToken() : null;
  const isFormData = options.body instanceof FormData;

  try {
    return await fetch(requestUrl(path), {
      ...options,
      headers: {
        Accept: "application/json",
        ...(isFormData ? {} : { "Content-Type": "application/json" }),
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
        ...options.headers,
      },
      signal: controller.signal,
    });
  } catch (cause) {
    if (cause instanceof ApiError) throw cause;
    if (externalSignal?.aborted) throw cause;
    if (didTimeout || cause.name === "AbortError") throw timeoutApiError(cause);
    if (cause instanceof TypeError) throw networkApiError(cause);
    throw cause;
  } finally {
    externalSignal?.removeEventListener("abort", abortFromCaller);
    window.clearTimeout(timeoutId);
  }
};

const normalizeRequestError = (error) =>
  error instanceof ApiError ? error : networkApiError(error);

const endExpiredSession = (error) => {
  if (!error.authenticationHandled) {
    const hadSession = sessionStore.hasSession();
    sessionStore.clear();
    reportApiError(error);
    if (hadSession) reportAuthenticationRequired(error);
    error.authenticationHandled = true;
  }
  throw error;
};

const refreshAccessToken = () => {
  if (refreshPromise) return refreshPromise;

  refreshPromise = (async () => {
    const refreshToken = sessionStore.getRefreshToken();
    if (!refreshToken) {
      throw new ApiError({
        message: "نشست شما منقضی شده است. دوباره وارد شوید.",
        status: 401,
        code: "REFRESH_TOKEN_MISSING",
      });
    }

    const response = await executeRequest(
      REFRESH_PATH,
      {
        method: "POST",
        body: JSON.stringify({ refresh_token: refreshToken }),
      },
      { includeAuth: false },
    );
    const payload = await parseResponse(response);
    if (
      typeof payload?.access_token !== "string" ||
      typeof payload?.refresh_token !== "string"
    ) {
      throw invalidResponseApiError({ status: response.status });
    }

    sessionStore.setSession({
      accessToken: payload.access_token,
      refreshToken: payload.refresh_token,
      expiresIn: payload.expires_in,
      refreshExpiresIn: payload.refresh_expires_in,
      user: payload.user,
    });
    return payload.access_token;
  })()
    .catch((error) => endExpiredSession(normalizeRequestError(error)))
    .finally(() => {
      refreshPromise = null;
    });

  return refreshPromise;
};

const canRefreshRequest = (path) => !PUBLIC_AUTH_PATHS.has(path);

const executeWithRefresh = async (path, options = {}) => {
  const refreshEligible = canRefreshRequest(path);
  if (refreshEligible && sessionStore.shouldRefreshAccessToken()) {
    await refreshAccessToken();
  }

  const tokenUsed = sessionStore.getToken();
  let response = await executeRequest(path, options);
  if (
    response.status === 401 &&
    refreshEligible &&
    sessionStore.getRefreshToken()
  ) {
    if (sessionStore.getToken() === tokenUsed) await refreshAccessToken();
    response = await executeRequest(path, options);
  }
  return response;
};

export const request = async (path, options = {}) => {
  const hadSession = sessionStore.hasSession();

  try {
    const response = await executeWithRefresh(path, options);
    return await parseResponse(response);
  } catch (error) {
    if (error?.name === "AbortError") throw error;
    return handleApiError(normalizeRequestError(error), { hadSession });
  }
};

export const requestBlob = async (path, options = {}) => {
  const hadSession = sessionStore.hasSession();

  try {
    const response = await executeWithRefresh(path, options);
    if (!response.ok) await parseResponse(response);

    return {
      blob: await response.blob(),
      filename:
        response.headers
          .get("content-disposition")
          ?.match(/filename="?([^";]+)"?/)?.[1] ?? "drawing.dwg",
    };
  } catch (error) {
    return handleApiError(normalizeRequestError(error), { hadSession });
  }
};

export const requestText = async (path, options = {}) => {
  const hadSession = sessionStore.hasSession();

  try {
    const response = await executeWithRefresh(path, options);
    if (!response.ok) await parseResponse(response);
    return await response.text();
  } catch (error) {
    return handleApiError(normalizeRequestError(error), { hadSession });
  }
};
