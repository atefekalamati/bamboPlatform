import { APP_CONFIG } from "../config/appConfig.js";

const createRequestUrl = (path) => `${APP_CONFIG.apiBaseUrl}${path}`;

const parseResponse = async (response) => {
  if (response.status === 204) return null;

  const payload = await response.json();

  if (!response.ok) {
    const requestError = new Error(payload.message ?? "درخواست ناموفق بود.");
    requestError.status = response.status;
    requestError.details = payload;
    throw requestError;
  }

  return payload;
};

export const request = async (path, options = {}) => {
  const abortController = new AbortController();
  const timeoutId = window.setTimeout(
    () => abortController.abort(),
    APP_CONFIG.requestTimeoutMs,
  );

  try {
    const response = await fetch(createRequestUrl(path), {
      ...options,
      headers: {
        Accept: "application/json",
        "Content-Type": "application/json",
        ...options.headers,
      },
      signal: abortController.signal,
    });

    return await parseResponse(response);
  } finally {
    window.clearTimeout(timeoutId);
  }
};

