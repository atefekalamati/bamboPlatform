import { authService } from "../services/authService.js";
import {
  isValidIranianMobile,
  maskPhoneNumber,
  normalizeDigits,
  normalizePhoneNumber,
} from "../utils/phoneNumber.js";

const createElement = (tagName, className, textContent = "") => {
  const element = document.createElement(tagName);

  element.className = className;
  element.textContent = textContent;

  return element;
};

const createField = ({ id, label, inputMode, autocomplete }) => {
  const field = createElement("div", "form-field");
  const fieldLabel = createElement("label", "form-field__label", label);
  const input = document.createElement("input");
  const error = createElement("p", "form-field__error");

  fieldLabel.htmlFor = id;
  input.id = id;
  input.className = "form-field__input";
  input.name = id;
  input.type = "text";
  input.inputMode = inputMode;
  input.autocomplete = autocomplete;
  input.required = true;
  input.setAttribute("aria-describedby", `${id}-error`);
  error.id = `${id}-error`;

  field.append(fieldLabel, input, error);

  return { field, input, error };
};

const setFieldError = ({ input, error }, message = "") => {
  error.textContent = message;
  input.setAttribute("aria-invalid", String(Boolean(message)));
};

const setSubmitState = (button, isSubmitting, loadingText) => {
  button.disabled = isSubmitting;
  button.textContent = isSubmitting ? loadingText : button.dataset.label;
};

export const LoginPage = () => {
  const page = createElement("div", "auth-card");
  const heading = createElement("h2", "auth-card__title", "ورود به BAMBO Pilot");
  const description = createElement(
    "p",
    "auth-card__description",
    "شماره موبایل خود را وارد کنید تا کد ورود برای شما ارسال شود.",
  );
  const feedback = createElement("div", "form-feedback");
  const form = document.createElement("form");
  const phoneField = createField({
    id: "phone-number",
    label: "شماره موبایل",
    inputMode: "tel",
    autocomplete: "tel",
  });
  const otpField = createField({
    id: "otp-code",
    label: "کد ورود",
    inputMode: "numeric",
    autocomplete: "one-time-code",
  });
  const submitButton = createElement("button", "button button--primary");
  const secondaryButton = createElement("button", "button button--ghost");
  const resendButton = createElement("button", "button button--ghost");
  let currentStep = "phone";
  let phoneNumber = "";

  form.className = "auth-form";
  form.noValidate = true;
  feedback.setAttribute("role", "status");
  feedback.setAttribute("aria-live", "polite");
  otpField.field.hidden = true;

  submitButton.type = "submit";
  submitButton.dataset.label = "ارسال کد ورود";
  submitButton.textContent = submitButton.dataset.label;

  secondaryButton.type = "button";
  secondaryButton.textContent = "اصلاح شماره موبایل";
  secondaryButton.hidden = true;

  resendButton.type = "button";
  resendButton.dataset.label = "ارسال مجدد کد";
  resendButton.textContent = resendButton.dataset.label;
  resendButton.hidden = true;

  const showFeedback = (message = "", type = "info") => {
    feedback.textContent = message;
    feedback.dataset.type = type;
    feedback.hidden = !message;
  };

  const showOtpStep = () => {
    currentStep = "otp";
    phoneField.field.hidden = true;
    otpField.field.hidden = false;
    secondaryButton.hidden = false;
    resendButton.hidden = false;
    submitButton.dataset.label = "تأیید و ورود";
    submitButton.textContent = submitButton.dataset.label;
    description.textContent = `کد ارسال‌شده به ${maskPhoneNumber(phoneNumber)} را وارد کنید.`;
    otpField.input.focus();
  };

  const showPhoneStep = () => {
    currentStep = "phone";
    otpField.field.hidden = true;
    phoneField.field.hidden = false;
    secondaryButton.hidden = true;
    resendButton.hidden = true;
    submitButton.dataset.label = "ارسال کد ورود";
    submitButton.textContent = submitButton.dataset.label;
    description.textContent =
      "شماره موبایل خود را وارد کنید تا کد ورود برای شما ارسال شود.";
    showFeedback();
    phoneField.input.focus();
  };

  const requestOtp = async () => {
    phoneNumber = normalizePhoneNumber(phoneField.input.value);
    phoneField.input.value = phoneNumber;

    if (!isValidIranianMobile(phoneNumber)) {
      setFieldError(phoneField, "شماره موبایل معتبر وارد کنید.");
      phoneField.input.focus();
      return;
    }

    setFieldError(phoneField);
    setSubmitState(submitButton, true, "در حال ارسال...");

    try {
      const response = await authService.requestOtp(phoneNumber);
      showFeedback(response.message, "success");
      showOtpStep();
    } catch (error) {
      showFeedback(error.message ?? "ارسال کد انجام نشد. دوباره تلاش کنید.", "error");
    } finally {
      setSubmitState(submitButton, false);
    }
  };

  const verifyOtp = async () => {
    const otpCode = normalizeDigits(otpField.input.value).trim();
    otpField.input.value = otpCode;

    if (!/^\d+$/.test(otpCode)) {
      setFieldError(otpField, "کد ورود را فقط با رقم وارد کنید.");
      otpField.input.focus();
      return;
    }

    setFieldError(otpField);
    setSubmitState(submitButton, true, "در حال بررسی...");

    try {
      const response = await authService.verifyOtp({ phoneNumber, otpCode });
      showFeedback(response.message, "success");
    } catch (error) {
      showFeedback(error.message ?? "کد ورود تأیید نشد.", "error");
    } finally {
      setSubmitState(submitButton, false);
    }
  };

  const resendOtp = async () => {
    setSubmitState(resendButton, true, "در حال ارسال...");

    try {
      const response = await authService.requestOtp(phoneNumber);
      showFeedback(response.message, "success");
      otpField.input.focus();
    } catch (error) {
      showFeedback(error.message ?? "ارسال مجدد کد انجام نشد.", "error");
    } finally {
      setSubmitState(resendButton, false);
    }
  };

  form.addEventListener("submit", async (event) => {
    event.preventDefault();

    if (currentStep === "phone") {
      await requestOtp();
      return;
    }

    await verifyOtp();
  });

  secondaryButton.addEventListener("click", showPhoneStep);
  resendButton.addEventListener("click", resendOtp);

  form.append(
    phoneField.field,
    otpField.field,
    submitButton,
    resendButton,
    secondaryButton,
  );
  page.append(heading, description, feedback, form);

  return page;
};
