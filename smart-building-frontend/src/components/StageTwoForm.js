import {
  isValidIranianMobile,
  normalizePhoneNumber,
} from "../utils/phoneNumber.js";

const CONSENTS = Object.freeze([
  { key: "introductionCompleted", label: "معرفی پایلوت انجام شد." },
  { key: "imagingAccepted", label: "موافقت تصویربرداری اخذ شد." },
  { key: "dwgAccepted", label: "ارائه نقشه پذیرفته شد." },
  { key: "feedbackAccepted", label: "ارائه بازخورد پذیرفته شد." },
]);

const field = ({ id, label, value = "", disabled, type = "text" }) => {
  const wrapper = document.createElement("div");
  const labelNode = document.createElement("label");
  const control = document.createElement(type === "textarea" ? "textarea" : "input");
  const error = document.createElement("p");
  wrapper.className = "stage-form__field";
  labelNode.className = "stage-form__label";
  labelNode.htmlFor = id;
  labelNode.textContent = label;
  control.id = id;
  control.className = "stage-form__control";
  control.value = value ?? "";
  control.disabled = disabled;
  error.className = "stage-form__error";
  error.id = `${id}-error`;
  control.setAttribute("aria-describedby", error.id);
  wrapper.append(labelNode, control, error);
  return { wrapper, control, error };
};

const setError = (target, message = "") => {
  target.error.textContent = message;
  target.control.setAttribute("aria-invalid", String(Boolean(message)));
};

export const StageTwoForm = ({ initialData, disabled, onChange }) => {
  const values = initialData ?? {};
  const form = document.createElement("form");
  const contactSection = document.createElement("fieldset");
  const contactLegend = document.createElement("legend");
  const contactGrid = document.createElement("div");
  const coordinatorName = field({
    id: "stage2-coordinator-name",
    label: "نام هماهنگ‌کننده سایت *",
    value: values.coordinatorName,
    disabled,
  });
  const coordinatorMobile = field({
    id: "stage2-coordinator-mobile",
    label: "موبایل هماهنگ‌کننده *",
    value: values.coordinatorMobile?.replace(/^\+98/, "0"),
    disabled,
  });
  const limitation = field({
    id: "stage2-limitation",
    label: "محدودیت‌ها",
    value: values.limitation,
    disabled,
    type: "textarea",
  });
  const referralDeadline = field({
    id: "stage2-referral-deadline",
    label: "مهلت ارجاع",
    value: values.referralDeadline,
    disabled,
  });
  const checklist = document.createElement("fieldset");
  const checklistLegend = document.createElement("legend");
  const checkboxes = new Map();
  const resultField = document.createElement("div");
  const resultLabel = document.createElement("label");
  const result = document.createElement("select");
  const resultError = document.createElement("p");

  form.className = "stage-form";
  contactSection.className = "stage-form__section";
  contactLegend.className = "stage-form__legend";
  contactLegend.textContent = "هماهنگی و محدودیت‌ها";
  contactGrid.className = "stage-form__grid";
  coordinatorMobile.control.inputMode = "tel";
  referralDeadline.control.type = "date";
  [coordinatorName, coordinatorMobile, limitation, referralDeadline].forEach(
    (target) => target.control.addEventListener("input", onChange),
  );
  contactGrid.append(
    coordinatorName.wrapper,
    coordinatorMobile.wrapper,
    limitation.wrapper,
    referralDeadline.wrapper,
  );
  contactSection.append(contactLegend, contactGrid);

  checklist.className = "checklist";
  checklistLegend.className = "checklist__legend";
  checklistLegend.textContent = "معرفی و موافقت‌ها";
  checklist.append(checklistLegend);
  CONSENTS.forEach(({ key, label }) => {
    const item = document.createElement("label");
    const checkbox = document.createElement("input");
    const text = document.createElement("span");
    item.className = "checklist__item";
    checkbox.type = "checkbox";
    checkbox.checked = Boolean(values[key]);
    checkbox.disabled = disabled;
    checkbox.addEventListener("change", () => {
      item.classList.remove("checklist__item--invalid");
      onChange();
    });
    text.textContent = `${label} *`;
    item.append(checkbox, text);
    checklist.append(item);
    checkboxes.set(key, { checkbox, item });
  });

  resultField.className = "stage-form__field";
  resultLabel.className = "stage-form__label";
  resultLabel.htmlFor = "stage2-result";
  resultLabel.textContent = "نتیجه نهایی F01 *";
  result.id = "stage2-result";
  result.className = "stage-form__control";
  result.disabled = disabled;
  result.append(
    new Option("نیازمند تکمیل اطلاعات", "complete_information"),
    new Option("تأییدشده", "approved"),
    new Option("ردشده", "rejected"),
    new Option("ارجاع‌شده", "referred"),
  );
  result.value = values.result ?? "complete_information";
  result.addEventListener("change", onChange);
  resultError.className = "stage-form__error";
  resultField.append(resultLabel, result, resultError);
  checklist.append(resultField);
  form.append(contactSection, checklist);

  const getData = () => ({
    ...values,
    coordinatorName: coordinatorName.control.value.trim(),
    coordinatorMobile: normalizePhoneNumber(coordinatorMobile.control.value),
    limitation: limitation.control.value.trim(),
    referralDeadline: referralDeadline.control.value || null,
    ...Object.fromEntries(
      [...checkboxes].map(([key, { checkbox }]) => [key, checkbox.checked]),
    ),
    result: result.value,
  });

  const validate = () => {
    const nameValid = coordinatorName.control.value.trim().length >= 2;
    const mobile = normalizePhoneNumber(coordinatorMobile.control.value);
    const mobileValid = isValidIranianMobile(mobile);
    const errors = [];
    setError(
      coordinatorName,
      nameValid ? "" : "نام هماهنگ‌کننده را وارد کنید.",
    );
    setError(
      coordinatorMobile,
      mobileValid ? "" : "شماره موبایل معتبر وارد کنید.",
    );
    coordinatorMobile.control.value = mobile;
    if (!nameValid) errors.push({ field: "coordinatorName" });
    if (!mobileValid) errors.push({ field: "coordinatorMobile" });
    checkboxes.forEach(({ checkbox, item }, key) => {
      item.classList.toggle("checklist__item--invalid", !checkbox.checked);
      if (!checkbox.checked) errors.push({ field: `checklist.${key}` });
    });
    const resultValid = result.value === "approved";
    resultError.textContent = resultValid
      ? ""
      : "برای عبور از G1، نتیجه F01 باید تأییدشده باشد.";
    result.setAttribute("aria-invalid", String(!resultValid));
    if (!resultValid) errors.push({ field: "result" });
    return errors;
  };

  return { element: form, getData, validate };
};
