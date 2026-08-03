import assert from "node:assert/strict";
import test from "node:test";
import { createF04FollowUpPayload } from "../src/services/experienceService.js";

const values = {
  ownerLoggedIn: true, projectOpened: true, mainTourViewed: true,
  viewingResult: "مشاهده موفق", firstFollowUpAt: "2026-08-03T08:00:00.000Z",
  secondFollowUpAt: "2026-08-04T08:00:00.000Z", useful: true,
  coverageScore: 8, qualityScore: 9, mostUsefulPart: "مسیر", missingPart: "",
  otherUsers: "", moreTrainingNeeded: false, satisfactionScore: 9,
  issueDescription: "", issueCategory: "", issueRoute: "", issueOwnerUserId: null,
  issueDueAt: "", customerSuccessUserId: 1,
};

test("includes the optional manual Stage 13 issue when the backend field is used", () => {
  const payload = createF04FollowUpPayload({ ...values, otherIssueDescription: "مشکل سفارشی" });
  assert.equal(payload.other_issue_description, "مشکل سفارشی");
});

test("can explicitly clear a supported optional manual issue", () => {
  const payload = createF04FollowUpPayload({ ...values, otherIssueDescription: "", otherIssueDescriptionSupported: true });
  assert.equal(payload.other_issue_description, null);
});

test("keeps the former backend contract for an untouched unsupported field", () => {
  const payload = createF04FollowUpPayload({ ...values, otherIssueDescription: "", otherIssueDescriptionSupported: false });
  assert.equal(Object.hasOwn(payload, "other_issue_description"), false);
});
