import assert from "node:assert/strict";
import test from "node:test";
import { translateActionTitle, translateAuditAction, translateDisplayValue } from "../src/utils/displayText.js";

test("translates dashboard action titles returned by backend", () => {
  assert.equal(translateActionTitle("complete stage 13"), "تکمیل مرحله 13");
  assert.equal(translateActionTitle("review stage 9"), "بازبینی مرحله 9");
  assert.equal(translateActionTitle("Mission requires action"), "مأموریت نیازمند اقدام");
  assert.equal(translateActionTitle("Incident requires action"), "رخداد نیازمند اقدام");
  assert.equal(translateActionTitle("Customer follow-up"), "پیگیری مشتری");
});

test("translates statuses, priorities and gate codes", () => {
  assert.equal(translateDisplayValue("needs_revision"), "نیازمند اصلاح");
  assert.equal(translateDisplayValue("HIGH"), "مهم");
  assert.equal(translateDisplayValue("G4"), "گیت 4");
});

test("never exposes an unknown technical English value", () => {
  assert.equal(translateDisplayValue("unknown_backend_state", "وضعیت نامشخص"), "وضعیت نامشخص");
  assert.equal(translateActionTitle("unknown backend operation"), "اقدام موردنیاز");
});

test("keeps Persian content and localizes known audit actions", () => {
  assert.equal(translateDisplayValue("در انتظار بررسی"), "در انتظار بررسی");
  assert.equal(translateAuditAction("forms.f04_saved"), "فرم — ذخیره شد");
});
