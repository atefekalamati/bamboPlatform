import assert from "node:assert/strict";
import test from "node:test";

import {
  isCallablePhoneNumber,
  toInternationalPhoneNumber,
} from "../src/utils/phoneNumber.js";

test("Iranian mobile numbers are normalized to an international tel value", () => {
  assert.equal(toInternationalPhoneNumber("۰۹۱۲-۱۲۳ ۴۵۶۷"), "+989121234567");
  assert.equal(toInternationalPhoneNumber("0098 912 123 4567"), "+989121234567");
  assert.equal(toInternationalPhoneNumber("+98 (912) 123-4567"), "+989121234567");
});

test("Iranian landline numbers are normalized to an international tel value", () => {
  assert.equal(toInternationalPhoneNumber("021-1234 5678"), "+982112345678");
});

test("masked and malformed values cannot become tel links", () => {
  assert.equal(toInternationalPhoneNumber("0912***4567"), "");
  assert.equal(toInternationalPhoneNumber("123"), "");
  assert.equal(isCallablePhoneNumber("0912 123 4567"), true);
});
