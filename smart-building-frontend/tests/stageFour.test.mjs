import assert from "node:assert/strict";
import test from "node:test";
import {
  CONTACTS_SUMMARY_CONFIRMATION,
  contactsSummaryFromConfirmation,
} from "../src/features/stages/stageFour.js";

test("maps the Stage 4 contact checkbox to the optional backend text field", () => {
  assert.equal(
    contactsSummaryFromConfirmation(true),
    CONTACTS_SUMMARY_CONFIRMATION,
  );
  assert.equal(contactsSummaryFromConfirmation(false), "");
});
