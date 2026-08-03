import { authService } from "../services/authService.js";
import { APP_CONFIG } from "../config/appConfig.js";
import {
  isValidIranianMobile,
  normalizeDigits,
  normalizePhoneNumber,
} from "../utils/phoneNumber.js";

const element = (tag, className, text = "") => {
  const node = document.createElement(tag);
  node.className = className;
  node.textContent = text;
  return node;
};

const field = ({ id, label, inputMode, autocomplete }) => {
  const wrapper = element("div", "form-field");
  const labelNode = element("label", "form-field__label", label);
  const input = document.createElement("input");
  const error = element("p", "form-field__error");

  labelNode.htmlFor = id;
  input.id = id;
  input.className = "form-field__input";
  input.type = "text";
  input.inputMode = inputMode;
  input.autocomplete = autocomplete;
  input.setAttribute("aria-describedby", `${id}-error`);
  error.id = `${id}-error`;
  wrapper.append(labelNode, input, error);
  return { wrapper, input, error };
};

const setFieldError = (target, message = "") => {
  target.error.textContent = message;
  target.input.setAttribute("aria-invalid", String(Boolean(message)));
};

const setBusy = (button, busy, loadingText = "") => {
  button.disabled = busy;
  button.textContent = busy ? loadingText : button.dataset.label;
};

export const LoginPage = ({ onAuthenticated } = {}) => {
  const page = element("div", "auth-card");
  const heading = element("h2", "auth-card__title", "ورود به BAMBO Pilot");
  const description = element(
    "p",
    "auth-card__description",
    "شماره موبایل خود را وارد کنید تا کد ورود برای شما ارسال شود.",
  );
  const feedback = element("div", "form-feedback");
  const form = document.createElement("form");
  const phoneField = field({
    id: "phone-number",
    label: "شماره موبایل",
    inputMode: "tel",
    autocomplete: "tel",
  });
  const otpField = field({
    id: "otp-code",
    label: "کد ورود",
    inputMode: "numeric",
    autocomplete: "one-time-code",
  });
  const submitButton = element("button", "button button--primary");
  const resendButton = element("button", "button button--ghost");
  const backButton = element("button", "button button--ghost", "اصلاح شماره موبایل");
  let step = "phone";
  let phoneNumber = "";
  let requestId = "";
  let destinationMask = "";
  let resendTimer = null;
  let expiresTimer = null;

  form.className = "auth-form";
  form.noValidate = true;
  feedback.setAttribute("role", "status");
  feedback.setAttribute("aria-live", "polite");
  otpField.wrapper.hidden = true;
  submitButton.type = "submit";
  submitButton.dataset.label = "ارسال کد ورود";
  submitButton.textContent = submitButton.dataset.label;
  resendButton.type = "button";
  resendButton.dataset.label = "ارسال مجدد کد";
  resendButton.textContent = resendButton.dataset.label;
  resendButton.hidden = true;
  backButton.type = "button";
  backButton.hidden = true;

  const showFeedback = (message = "", type = "info") => {
    feedback.textContent = message;
    feedback.dataset.type = type;
    feedback.hidden = !message;
  };

  const showOtpStep = () => {
    step = "otp";
    phoneField.wrapper.hidden = true;
    otpField.wrapper.hidden = false;
    resendButton.hidden = false;
    backButton.hidden = false;
    submitButton.dataset.label = "تأیید و ورود";
    submitButton.textContent = submitButton.dataset.label;
    description.textContent = `کد شش‌رقمی ارسال‌شده به ${destinationMask || phoneNumber} را وارد کنید.`;
    otpField.input.focus();
  };

  const showPhoneStep = () => {
    step = "phone";
    requestId = "";
    window.clearInterval(resendTimer);
    window.clearTimeout(expiresTimer);
    submitButton.disabled = false;
    destinationMask = "";
    otpField.wrapper.hidden = true;
    phoneField.wrapper.hidden = false;
    resendButton.hidden = true;
    backButton.hidden = true;
    submitButton.dataset.label = "ارسال کد ورود";
    submitButton.textContent = submitButton.dataset.label;
    description.textContent =
      "شماره موبایل خود را وارد کنید تا کد ورود برای شما ارسال شود.";
    showFeedback();
    phoneField.input.focus();
  };

  const displayOtpResponse = (response, fallbackMessage) => {
    requestId = response.request_id;
    destinationMask = response.destination_mask;
    submitButton.disabled = false;
    const developmentCode = APP_CONFIG.isProduction
      ? ""
      : String(response["debug" + "_code"] ?? "").trim();
    const feedbackMessage = developmentCode
      ? `${fallbackMessage} کد ورود محیط توسعه: ${developmentCode}`
      : fallbackMessage;
    showFeedback(feedbackMessage, "success");
    window.clearInterval(resendTimer);
    window.clearTimeout(expiresTimer);
    let remaining = Math.max(0, Number(response.retry_after) || 0);
    const updateCooldown = () => {
      resendButton.textContent = remaining > 0
        ? `ارسال مجدد تا ${remaining} ثانیه`
        : resendButton.dataset.label;
      resendButton.disabled = remaining > 0;
      if (remaining <= 0) window.clearInterval(resendTimer);
      remaining -= 1;
    };
    updateCooldown();
    resendTimer = window.setInterval(updateCooldown, 1000);
    expiresTimer = window.setTimeout(() => {
      requestId = "";
      otpField.input.value = "";
      submitButton.disabled = true;
      showFeedback("زمان اعتبار کد پایان یافت؛ کد جدید دریافت کنید.", "error");
    }, Math.max(1, Number(response.expires_in) || 300) * 1000);
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
    setBusy(submitButton, true, "در حال ارسال...");
    try {
      const response = await authService.requestOtp(phoneNumber);
      displayOtpResponse(response, "کد ورود ارسال شد.");
      showOtpStep();
    } catch (error) {
      showFeedback(error.message ?? "ارسال کد انجام نشد. دوباره تلاش کنید.", "error");
    } finally {
      setBusy(submitButton, false);
    }
  };

  const verifyOtp = async () => {
    const code = normalizeDigits(otpField.input.value).trim();
    otpField.input.value = code;
    if (!/^\d{6}$/.test(code)) {
      setFieldError(otpField, "کد ورود باید شش رقم باشد.");
      otpField.input.focus();
      return;
    }

    setFieldError(otpField);
    setBusy(submitButton, true, "در حال بررسی...");
    try {
      await authService.verifyOtp({ requestId, code });
      window.clearInterval(resendTimer);
      window.clearTimeout(expiresTimer);
      otpField.input.value = "";
      requestId = "";
      showFeedback("ورود با موفقیت انجام شد.", "success");
      await onAuthenticated?.();
    } catch (error) {
      showFeedback(error.message ?? "کد ورود تأیید نشد.", "error");
    } finally {
      setBusy(submitButton, false);
    }
  };

  const resendOtp = async () => {
    setBusy(resendButton, true, "در حال ارسال...");
    try {
      const response = await authService.requestOtp(phoneNumber);
      displayOtpResponse(response, "کد جدید ارسال شد.");
      otpField.input.focus();
    } catch (error) {
      showFeedback(error.message ?? "ارسال مجدد کد انجام نشد.", "error");
    } finally {
      setBusy(resendButton, false);
    }
  };

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    await (step === "phone" ? requestOtp() : verifyOtp());
  });
  resendButton.addEventListener("click", resendOtp);
  backButton.addEventListener("click", showPhoneStep);

  form.append(
    phoneField.wrapper,
    otpField.wrapper,
    submitButton,
    resendButton,
    backButton,
  );
  page.append(heading, description, feedback, form);
  return page;
};
