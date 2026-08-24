import { request } from "./httpClient.js";
import { toBackendUtcDateTime } from "../utils/jalaliDateTime.js";

export const CALL_OUTCOMES = Object.freeze([
  "customer_confirmed", "revision_requested", "callback_requested", "no_response",
  "customer_rejected", "invalid_contact", "escalated_to_manager",
  "contract_follow_up", "follow_up_completed",
]);

export const mapCall = (call) => ({
  id: call.public_id,
  pilotId: call.pilot_id,
  stageNumber: call.stage_number,
  destinationMasked: call.destination_masked,
  purpose: call.purpose,
  technicalStatus: call.technical_status,
  businessOutcome: call.business_outcome,
  summary: call.summary,
  nextAction: call.next_action,
  callbackAt: call.callback_at,
  recordingConsent: Boolean(call.recording_consent),
  overriddenAt: call.overridden_at,
  requestedAt: call.requested_at,
  startedAt: call.started_at,
  answeredAt: call.answered_at,
  endedAt: call.ended_at,
  durationSeconds: call.duration_seconds,
  attempts: Array.isArray(call.attempts) ? call.attempts : [],
});

const idempotencyKey = () => globalThis.crypto?.randomUUID?.()
  ?? `call-${Date.now()}-${Math.random().toString(16).slice(2)}`;

export const callService = Object.freeze({
  list: async (pilotId, stageNumber) => {
    const response = await request(`/api/v1/pilots/${pilotId}/stages/${stageNumber}/calls`);
    if (!Array.isArray(response)) throw new TypeError("پاسخ فهرست تماس‌ها معتبر نیست.");
    return response.map(mapCall);
  },
  initiate: async (pilotId, stageNumber, { purpose, recordingConsent }) => mapCall(await request(
    `/api/v1/pilots/${pilotId}/stages/${stageNumber}/calls`,
    {
      method: "POST",
      body: JSON.stringify({
        purpose: purpose?.trim() || null,
        recording_consent: Boolean(recordingConsent),
        idempotency_key: idempotencyKey(),
      }),
    },
  )),
  recordOutcome: async (callId, values) => mapCall(await request(
    `/api/v1/calls/${encodeURIComponent(callId)}/outcome`,
    {
      method: "PATCH",
      body: JSON.stringify({
        outcome: values.outcome,
        summary: values.summary.trim(),
        next_action: values.nextAction?.trim() || null,
        callback_at: values.callbackAt ? toBackendUtcDateTime(values.callbackAt) : null,
      }),
    },
  )),
  retry: async (callId) => mapCall(await request(
    `/api/v1/calls/${encodeURIComponent(callId)}/retry`, { method: "POST" },
  )),
  override: async (callId, reason) => mapCall(await request(
    `/api/v1/calls/${encodeURIComponent(callId)}/override`,
    { method: "POST", body: JSON.stringify({ reason: reason.trim() }) },
  )),
  getRecordingReference: (callId) => request(
    `/api/v1/calls/${encodeURIComponent(callId)}/recording-reference`,
  ),
});
