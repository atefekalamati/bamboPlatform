import assert from "node:assert/strict";
import test from "node:test";
import {
  buildPilotCreatePayload,
  PROJECT_PROGRESS_STAGES,
} from "../src/features/pilots/pilotCreation.js";

test("offers exactly the approved project progress stages", () => {
  assert.deepEqual(PROJECT_PROGRESS_STAGES, [
    "تخریب ساختمان قدیمی",
    "تجهیز کارگاه",
    "خاکبرداری",
    "سازه نگهبان",
    "فونداسیون",
    "دیوارهای حائل",
    "اجرای سازه بتنی",
    "اجرای سازه فولادی",
    "سفتکاری",
    "کفسازی",
    "تاسیسات مکانیکی",
    "تاسیسات الکتریکی",
    "نازک کاری واحدهای مسکونی",
    "دکوراسیون",
    "نصبیات تاسیسات مکانیکی و الکتریکی",
    "آسانسور",
    "نمای ساختمان و پنجره ها",
    "فضای عمومی",
    "تجهیزات عمومی و زیربنایی تاسیسات",
    "نظافت و برچیدن کارگاه",
  ]);
});

test("uses the case title as the backend project name", () => {
  const payload = buildPilotCreatePayload({
    displayName: "پرونده برج بامبو",
    pilotYear: 1405,
    ownerName: "مالک نمونه",
    decisionMakerName: "تصمیم‌گیرنده نمونه",
    decisionMakerPosition: "مدیر پروژه",
    primaryMobile: "+989121234567",
    totalFloors: 12,
    address: "تهران، خیابان نمونه",
    progressStage: "فونداسیون",
    customerNeed: "برداشت ساختمان",
    expectedValue: "بازدید غیرحضوری",
    projectName: "این مقدار قدیمی نباید استفاده شود",
  });

  assert.equal(payload.display_name, "پرونده برج بامبو");
  assert.equal(payload.project.name, "پرونده برج بامبو");
  assert.equal(payload.project.progress_stage, "فونداسیون");
  assert.equal(JSON.stringify(payload).includes("این مقدار قدیمی"), false);
});
