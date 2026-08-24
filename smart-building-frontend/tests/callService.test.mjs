import test from "node:test";
import assert from "node:assert/strict";
import { CALL_OUTCOMES, mapCall } from "../src/services/callService.js";
import { stageEighteenSubmissionErrorMessage } from "../src/pages/StageEighteenPage.js";

test("maps the backend call contract without exposing a full destination", () => {
  const result = mapCall({
    public_id: "call-1", pilot_id: 4, stage_number: 18,
    destination_masked: "+989***1234", technical_status: "completed",
    business_outcome: "customer_confirmed", recording_consent: true,
    attempts: [{ attempt_number: 1 }],
  });
  assert.equal(result.id, "call-1");
  assert.equal(result.destinationMasked, "+989***1234");
  assert.equal(result.technicalStatus, "completed");
  assert.equal(result.attempts.length, 1);
  assert.equal("destination_phone" in result, false);
});

test("keeps every backend-supported business outcome", () => {
  assert.deepEqual(CALL_OUTCOMES, [
    "customer_confirmed", "revision_requested", "callback_requested", "no_response",
    "customer_rejected", "invalid_contact", "escalated_to_manager",
    "contract_follow_up", "follow_up_completed",
  ]);
});

test("explains the backend Stage 18 call requirement without changing its gate", () => {
  const message = stageEighteenSubmissionErrorMessage({
    code: "STAGE_VALIDATION_FAILED",
    errors: [{ field: "checklist.call_policy_completed", reason: "required" }],
  });
  assert.match(message, /تماس پاسخ‌داده‌شده یا تکمیل‌شده/);
  assert.match(message, /Override/);
  assert.equal(stageEighteenSubmissionErrorMessage({ message: "خطای دیگر" }), "خطای دیگر");
});
