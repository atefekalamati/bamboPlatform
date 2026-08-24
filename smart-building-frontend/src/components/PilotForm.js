import { PROJECT_PROGRESS_STAGES } from "../features/pilots/pilotCreation.js";
import {
  isValidIranianMobile,
  normalizeDigits,
  normalizePhoneNumber,
} from "../utils/phoneNumber.js";

const field = ({ id, label, type = "text" }) => {
  const wrapper = document.createElement("div");
  const labelNode = document.createElement("label");
  const control = document.createElement(type === "textarea" ? "textarea" : "input");
  const error = document.createElement("p");
  wrapper.className = "form-field";
  labelNode.className = "form-field__label";
  labelNode.htmlFor = id;
  labelNode.textContent = label;
  control.id = id;
  control.className = "form-field__input";
  error.className = "form-field__error";
  error.id = `${id}-error`;
  control.setAttribute("aria-describedby", error.id);
  wrapper.append(labelNode, control, error);
  return { wrapper, control, error };
};

const selectField = ({ id, label, options }) => {
  const wrapper = document.createElement("div");
  const labelNode = document.createElement("label");
  const control = document.createElement("select");
  const placeholder = document.createElement("option");
  const error = document.createElement("p");
  wrapper.className = "form-field";
  labelNode.className = "form-field__label";
  labelNode.htmlFor = id;
  labelNode.textContent = label;
  control.id = id;
  control.className = "form-field__input";
  control.required = true;
  placeholder.value = "";
  placeholder.textContent = "مرحله پیشرفت پروژه را انتخاب کنید";
  placeholder.disabled = true;
  placeholder.selected = true;
  control.append(placeholder);
  options.forEach((value) => {
    const option = document.createElement("option");
    option.value = value;
    option.textContent = value;
    control.append(option);
  });
  error.className = "form-field__error";
  error.id = `${id}-error`;
  control.setAttribute("aria-describedby", error.id);
  wrapper.append(labelNode, control, error);
  return { wrapper, control, error };
};

const setError = (target, message = "") => {
  target.error.textContent = message;
  target.control.setAttribute("aria-invalid", String(Boolean(message)));
};

export const PilotForm = ({ onSubmit, onCancel }) => {
  const form = document.createElement("form");
  const feedback = document.createElement("div");
  const displayName = field({ id: "pilot-display-name", label: "عنوان پرونده" });
  const pilotYear = field({ id: "pilot-year", label: "سال پایلوت" });
  const ownerName = field({ id: "owner-name", label: "نام مالک" });
  const decisionMakerName = field({
    id: "decision-maker-name",
    label: "نام تصمیم‌گیرنده",
  });
  const decisionMakerPosition = field({
    id: "decision-maker-position",
    label: "سمت تصمیم‌گیرنده",
  });
  const primaryMobile = field({ id: "owner-mobile", label: "موبایل اصلی" });
  const totalFloors = field({ id: "total-floors", label: "تعداد طبقات" });
  const address = field({ id: "project-address", label: "آدرس", type: "textarea" });
  const progressStage = selectField({
    id: "progress-stage",
    label: "مرحله پیشرفت پروژه",
    options: PROJECT_PROGRESS_STAGES,
  });
  const customerNeed = field({
    id: "customer-need",
    label: "نیاز مشتری",
    type: "textarea",
  });
  const expectedValue = field({
    id: "expected-value",
    label: "ارزش مورد انتظار",
    type: "textarea",
  });
  const actions = document.createElement("div");
  const submit = document.createElement("button");
  const cancel = document.createElement("button");
  const requiredTextFields = [
    { target: displayName, min: 2, max: 160 },
    { target: ownerName, min: 2, max: 160 },
    { target: decisionMakerName, min: 2, max: 120 },
    { target: decisionMakerPosition, min: 2, max: 120 },
    { target: address, min: 5, max: 500 },
    { target: customerNeed, min: 2, max: 4000 },
    { target: expectedValue, min: 2, max: 4000 },
  ];

  form.className = "pilot-form";
  form.noValidate = true;
  feedback.className = "form-feedback";
  feedback.hidden = true;
  primaryMobile.control.inputMode = "tel";
  totalFloors.control.inputMode = "numeric";
  pilotYear.control.inputMode = "numeric";
  actions.className = "form-actions";
  submit.className = "button button--primary";
  submit.type = "submit";
  submit.textContent = "ایجاد پرونده";
  cancel.className = "button button--ghost";
  cancel.type = "button";
  cancel.textContent = "انصراف";

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const mobile = normalizePhoneNumber(primaryMobile.control.value);
    const floors = Number(normalizeDigits(totalFloors.control.value));
    const yearText = normalizeDigits(pilotYear.control.value).trim();
    const year = yearText ? Number(yearText) : null;
    let valid = true;

    requiredTextFields.forEach(({ target, min, max }) => {
      const value = target.control.value.trim();
      const fieldValid = value.length >= min && value.length <= max;
      setError(
        target,
        fieldValid ? "" : `این فیلد باید بین ${min} تا ${max} کاراکتر باشد.`,
      );
      valid &&= fieldValid;
    });
    const mobileValid = isValidIranianMobile(mobile);
    const floorsValid = Number.isInteger(floors) && floors >= 1 && floors <= 500;
    const yearValid = year === null || (year >= 1300 && year <= 2000);
    const progressStageValid = PROJECT_PROGRESS_STAGES.includes(
      progressStage.control.value,
    );
    setError(primaryMobile, mobileValid ? "" : "شماره موبایل معتبر وارد کنید.");
    setError(totalFloors, floorsValid ? "" : "عددی بین ۱ تا ۵۰۰ وارد کنید.");
    setError(pilotYear, yearValid ? "" : "سال باید بین ۱۳۰۰ تا ۲۰۰۰ باشد.");
    setError(
      progressStage,
      progressStageValid ? "" : "یکی از مراحل پیشرفت تعریف‌شده را انتخاب کنید.",
    );
    valid &&= mobileValid && floorsValid && yearValid && progressStageValid;
    primaryMobile.control.value = mobile;
    if (!valid) return;

    submit.disabled = true;
    submit.textContent = "در حال ایجاد...";
    feedback.hidden = true;
    try {
      await onSubmit({
        displayName: displayName.control.value.trim(),
        pilotYear: year,
        ownerName: ownerName.control.value.trim(),
        decisionMakerName: decisionMakerName.control.value.trim(),
        decisionMakerPosition: decisionMakerPosition.control.value.trim(),
        primaryMobile: mobile,
        totalFloors: floors,
        address: address.control.value.trim(),
        progressStage: progressStage.control.value,
        customerNeed: customerNeed.control.value.trim(),
        expectedValue: expectedValue.control.value.trim(),
      });
    } catch (error) {
      feedback.textContent = error.message ?? "ایجاد پرونده انجام نشد.";
      feedback.dataset.type = "error";
      feedback.hidden = false;
      submit.disabled = false;
      submit.textContent = "ایجاد پرونده";
    }
  });

  cancel.addEventListener("click", onCancel);
  actions.append(submit, cancel);
  form.append(
    feedback,
    displayName.wrapper,
    pilotYear.wrapper,
    ownerName.wrapper,
    decisionMakerName.wrapper,
    decisionMakerPosition.wrapper,
    primaryMobile.wrapper,
    totalFloors.wrapper,
    address.wrapper,
    progressStage.wrapper,
    customerNeed.wrapper,
    expectedValue.wrapper,
    actions,
  );
  return form;
};
