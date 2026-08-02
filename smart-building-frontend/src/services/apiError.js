const STATUS_MESSAGES = Object.freeze({
  400: "اطلاعات ارسال‌شده معتبر نیست.",
  401: "نشست شما منقضی شده است. دوباره وارد شوید.",
  403: "برای انجام این عملیات دسترسی لازم را ندارید.",
  404: "اطلاعات موردنظر پیدا نشد.",
  409: "اطلاعات تغییر کرده است. وضعیت جدید را بررسی و دوباره تلاش کنید.",
  413: "حجم فایل بیشتر از حد مجاز است.",
  415: "نوع فایل پشتیبانی نمی‌شود.",
  422: "اطلاعات واردشده نیاز به اصلاح دارد.",
  429: "تعداد درخواست‌ها بیش از حد مجاز است. کمی بعد دوباره تلاش کنید.",
  500: "خطایی در سرور رخ داد. دوباره تلاش کنید.",
  502: "پاسخ سرور قابل پردازش نیست.",
  503: "سرویس موقتاً در دسترس نیست.",
});

const normalizeFieldPath = (location) => {
  if (!Array.isArray(location)) return null;
  const path = location.filter((part) => !["body", "query", "path"].includes(part));
  return path.length ? path.join(".") : null;
};

const normalizeErrorItem = (item) => {
  if (!item || typeof item !== "object") return null;

  const field = item.field ?? normalizeFieldPath(item.loc);
  return {
    field: field ? String(field) : null,
    label: item.label ? String(item.label) : null,
    reason: String(item.reason ?? item.msg ?? item.type ?? "invalid"),
  };
};

export const normalizeFieldErrors = (payload) => {
  const source = Array.isArray(payload?.errors)
    ? payload.errors
    : Array.isArray(payload?.detail)
      ? payload.detail
      : [];

  return source.map(normalizeErrorItem).filter(Boolean);
};

const responseMessage = (status, payload) => {
  if (typeof payload?.message === "string" && payload.message.trim()) {
    return payload.message.trim();
  }

  if (typeof payload?.detail === "string" && payload.detail.trim()) {
    return payload.detail.trim();
  }

  return STATUS_MESSAGES[status] ?? "درخواست ناموفق بود.";
};

export class ApiError extends Error {
  constructor({
    message,
    status = 0,
    code = "API_ERROR",
    stage = null,
    errors = [],
    traceId = null,
    retryAfter = null,
    details = null,
    cause,
  }) {
    super(message, cause ? { cause } : undefined);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
    this.stage = stage;
    this.errors = errors;
    this.traceId = traceId;
    this.retryAfter = retryAfter;
    this.details = details;
  }

  get isAuthenticationError() {
    return this.status === 401;
  }

  get isAuthorizationError() {
    return this.status === 403;
  }

  get isConflict() {
    return this.status === 409;
  }

  get isValidationError() {
    return this.status === 422 || this.errors.length > 0;
  }
}

export const apiErrorFromResponse = ({ status, payload }) =>
  new ApiError({
    message: responseMessage(status, payload),
    status,
    code: payload?.code ?? `HTTP_${status}`,
    stage: Number.isInteger(payload?.stage) ? payload.stage : null,
    errors: normalizeFieldErrors(payload),
    traceId: payload?.trace_id ?? null,
    retryAfter:
      Number.isFinite(Number(payload?.retry_after))
        ? Number(payload.retry_after)
        : null,
    details: payload,
  });

export const timeoutApiError = (cause) =>
  new ApiError({
    message: "زمان پاسخ‌گویی سرور به پایان رسید. دوباره تلاش کنید.",
    code: "REQUEST_TIMEOUT",
    cause,
  });

export const networkApiError = (cause) =>
  new ApiError({
    message: "ارتباط با سرور برقرار نشد. اتصال شبکه و اجرای Backend را بررسی کنید.",
    code: "NETWORK_ERROR",
    cause,
  });

export const invalidResponseApiError = ({ status, cause }) =>
  new ApiError({
    message: STATUS_MESSAGES[502],
    status,
    code: "INVALID_SERVER_RESPONSE",
    cause,
  });
