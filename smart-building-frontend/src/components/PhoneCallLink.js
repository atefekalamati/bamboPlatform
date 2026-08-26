import { toInternationalPhoneNumber } from "../utils/phoneNumber.js";

export const PhoneCallLink = ({
  phoneNumber,
  label,
  className = "phone-call-link",
  ariaLabel,
} = {}) => {
  const displayValue = label || String(phoneNumber ?? "");
  const internationalNumber = toInternationalPhoneNumber(phoneNumber);

  if (!internationalNumber) {
    const text = document.createElement("span");
    text.className = `${className} phone-call-link--unavailable`;
    text.textContent = displayValue || "شماره تماس ثبت نشده است";
    return text;
  }

  const link = document.createElement("a");
  link.className = className;
  link.href = `tel:${internationalNumber}`;
  link.textContent = displayValue;
  link.setAttribute("aria-label", ariaLabel || `تماس با شماره ${displayValue}`);
  link.title = `تماس با ${displayValue}`;
  return link;
};
