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

const handleApiError = (error, { hadToken }) => {
  reportApiError(error);

  if (error.status === 401 && hadToken) {
    sessionStore.clear();
    reportAuthenticationRequired(error);
  }

  throw error;
};

const executeRequest = async (path, options = {}) => {
  const controller = new AbortController();
  const externalSignal = options.signal;
  const abortFromCaller = () => controller.abort();
  externalSignal?.addEventListener("abort", abortFromCaller, { once: true });
  let didTimeout = false;
  const timeoutId = window.setTimeout(() => {
    didTimeout = true;
    controller.abort();
  }, APP_CONFIG.requestTimeoutMs);
  const token = sessionStore.getToken();
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

export const request = async (path, options = {}) => {
  const hadToken = Boolean(sessionStore.getToken());

  try {
    const response = await executeRequest(path, options);
    return await parseResponse(response);
  } catch (error) {
    if (error?.name === "AbortError") throw error;
    const apiError =
      error instanceof ApiError ? error : networkApiError(error);
    return handleApiError(apiError, { hadToken });
  }
};

export const requestBlob = async (path, options = {}) => {
  const hadToken = Boolean(sessionStore.getToken());

  try {
    const response = await executeRequest(path, options);
    if (!response.ok) await parseResponse(response);

    return {
      blob: await response.blob(),
      filename:
        response.headers
          .get("content-disposition")
          ?.match(/filename="?([^";]+)"?/)?.[1] ?? "drawing.dwg",
    };
  } catch (error) {
    const apiError =
      error instanceof ApiError ? error : networkApiError(error);
    return handleApiError(apiError, { hadToken });
  }
};
