import assert from "node:assert/strict";
import test from "node:test";

import {
  ApiError,
  apiErrorFromResponse,
  networkApiError,
  normalizeFieldErrors,
  timeoutApiError,
} from "../src/services/apiError.js";

test("normalizes the BAMBO stage validation contract", () => {
  const error = apiErrorFromResponse({
    status: 422,
    payload: {
      code: "STAGE_VALIDATION_FAILED",
      message: "مرحله قابل تأیید نیست.",
      stage: 3,
      trace_id: "trace-123",
      errors: [
        {
          field: "floors.3.dwg_file",
          label: "فایل DWG طبقه سوم",
          reason: "required",
        },
      ],
    },
  });

  assert.ok(error instanceof ApiError);
  assert.equal(error.status, 422);
  assert.equal(error.code, "STAGE_VALIDATION_FAILED");
  assert.equal(error.stage, 3);
  assert.equal(error.traceId, "trace-123");
  assert.equal(error.errors[0].field, "floors.3.dwg_file");
  assert.equal(error.isValidationError, true);
});

test("normalizes FastAPI validation details", () => {
  const errors = normalizeFieldErrors({
    detail: [
      {
        loc: ["body", "display_name"],
        msg: "Field required",
        type: "missing",
      },
    ],
  });

  assert.deepEqual(errors, [
    { field: "display_name", label: null, reason: "Field required" },
  ]);
});

test("keeps conflict metadata without retrying the operation", () => {
  const error = apiErrorFromResponse({
    status: 409,
    payload: {
      code: "STAGE_CONFLICT",
      message: "مرحله قبلاً تغییر کرده است.",
      errors: [],
    },
  });

  assert.equal(error.isConflict, true);
  assert.equal(error.message, "مرحله قبلاً تغییر کرده است.");
});

test("provides safe status fallback messages", () => {
  const forbidden = apiErrorFromResponse({ status: 403, payload: null });
  const rateLimited = apiErrorFromResponse({
    status: 429,
    payload: { retry_after: 45 },
  });

  assert.equal(forbidden.isAuthorizationError, true);
  assert.equal(rateLimited.retryAfter, 45);
  assert.match(rateLimited.message, /درخواست/);
});

test("distinguishes timeout and network failures", () => {
  assert.equal(timeoutApiError(new Error()).code, "REQUEST_TIMEOUT");
  assert.equal(networkApiError(new TypeError()).code, "NETWORK_ERROR");
});
