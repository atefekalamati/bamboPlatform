import { sessionStore } from "../app/sessionStore.js";
import { APP_CONFIG } from "../config/appConfig.js";

const requestUrl = (path) => `${APP_CONFIG.apiBaseUrl}${path}`;

const parseResponse = async (response) => {
  if (response.status === 204) return null;
  const payload = await response.json();
  if (response.ok) return payload;

  const validationMessage = Array.isArray(payload.detail)
    ? payload.detail[0]?.msg
    : payload.detail;
  const error = new Error(
    payload.message ?? validationMessage ?? "درخواست ناموفق بود.",
  );
  error.status = response.status;
  error.details = payload;
  throw error;
};

export const request = async (path, options = {}) => {
  const controller = new AbortController();
  const timeoutId = window.setTimeout(
    () => controller.abort(),
    APP_CONFIG.requestTimeoutMs,
  );

  try {
    const token = sessionStore.getToken();
    const isFormData = options.body instanceof FormData;
    const response = await fetch(requestUrl(path), {
      ...options,
      headers: {
        Accept: "application/json",
        ...(isFormData ? {} : { "Content-Type": "application/json" }),
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
        ...options.headers,
      },
      signal: controller.signal,
    });
    return await parseResponse(response);
  } catch (error) {
    if (error.name === "AbortError") {
      throw new Error("زمان پاسخ‌گویی سرور به پایان رسید.");
    }
    throw error;
  } finally {
    window.clearTimeout(timeoutId);
  }
};
