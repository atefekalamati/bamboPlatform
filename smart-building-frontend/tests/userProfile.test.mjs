import assert from "node:assert/strict";
import test from "node:test";
import { buildUserNamePatch } from "../src/features/users/userProfile.js";

test("نام تغییرکرده را برای API آماده می‌کند", () => {
  assert.deepEqual(
    buildUserNamePatch({ currentDisplayName: "کاربر قبلی", displayName: "  کاربر جدید  " }),
    { payload: { display_name: "کاربر جدید" }, errors: {} },
  );
});

test("شماره تلفن هیچ‌گاه وارد payload ویرایش نام نمی‌شود", () => {
  assert.deepEqual(
    buildUserNamePatch({
      currentDisplayName: "کاربر قبلی",
      displayName: "کاربر جدید",
      mobile: "09121234567",
    }),
    { payload: { display_name: "کاربر جدید" }, errors: {} },
  );
});

test("نام نامعتبر و نبود تغییر را گزارش می‌کند", () => {
  assert.equal(
    buildUserNamePatch({ currentDisplayName: "نام فعلی", displayName: "ن" }).errors.displayName,
    "نام باید بین ۲ تا ۱۲۰ کاراکتر باشد.",
  );
  assert.equal(
    buildUserNamePatch({ currentDisplayName: "نام فعلی", displayName: "نام فعلی" }).errors.form,
    "تغییری برای ذخیره ثبت نشده است.",
  );
});
