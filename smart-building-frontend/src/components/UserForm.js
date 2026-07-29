import {
  isValidIranianMobile,
  normalizePhoneNumber,
} from "../utils/phoneNumber.js";

const STATUS_OPTIONS = Object.freeze([
  { value: "active", label: "فعال" },
  { value: "inactive", label: "غیرفعال" },
  { value: "locked", label: "قفل‌شده" },
]);

const createField = ({ id, label, type = "text" }) => {
  const field = document.createElement("div");
  const fieldLabel = document.createElement("label");
  const control = document.createElement(type === "select" ? "select" : "input");
  const error = document.createElement("p");

  field.className = "form-field";
  fieldLabel.className = "form-field__label";
  fieldLabel.htmlFor = id;
  fieldLabel.textContent = label;
  control.id = id;
  control.name = id;
  control.className = "form-field__input";
  control.required = true;
  error.id = `${id}-error`;
  error.className = "form-field__error";
  control.setAttribute("aria-describedby", error.id);
  field.append(fieldLabel, control, error);

  return { field, control, error };
};

const appendOptions = (select, options) => {
  options.forEach(({ value, label }) => {
    const option = document.createElement("option");
    option.value = value;
    option.textContent = label;
    select.append(option);
  });
};

const setError = (field, message = "") => {
  field.error.textContent = message;
  field.control.setAttribute("aria-invalid", String(Boolean(message)));
};

export const UserForm = ({ user, roles, onSubmit, onCancel }) => {
  const form = document.createElement("form");
  const feedback = document.createElement("div");
  const actions = document.createElement("div");
  const submitButton = document.createElement("button");
  const cancelButton = document.createElement("button");
  const nameField = createField({ id: "full-name", label: "نام و نام خانوادگی" });
  const phoneField = createField({ id: "user-phone", label: "شماره موبایل" });
  const roleField = createField({ id: "user-role", label: "نقش", type: "select" });
  const statusField = createField({
    id: "user-status",
    label: "وضعیت حساب",
    type: "select",
  });

  form.className = "user-form";
  form.noValidate = true;
  feedback.className = "form-feedback";
  feedback.hidden = true;
  feedback.setAttribute("role", "alert");
  actions.className = "form-actions";
  submitButton.className = "button button--primary";
  submitButton.type = "submit";
  submitButton.textContent = user ? "ذخیره تغییرات" : "ایجاد کاربر";
  cancelButton.className = "button button--ghost";
  cancelButton.type = "button";
  cancelButton.textContent = "انصراف";
  phoneField.control.inputMode = "tel";
  phoneField.control.autocomplete = "tel";

  appendOptions(
    roleField.control,
    roles.map((role) => ({
      value: role.id,
      label: role.displayName ?? role.name,
    })),
  );
  appendOptions(statusField.control, STATUS_OPTIONS);

  nameField.control.value = user?.fullName ?? "";
  phoneField.control.value = user?.phoneNumber ?? "";
  roleField.control.value = user?.roleId ?? roles[0]?.id ?? "";
  statusField.control.value = user?.status ?? "active";

  const validate = () => {
    const fullName = nameField.control.value.trim();
    const phoneNumber = normalizePhoneNumber(phoneField.control.value);

    setError(nameField, fullName ? "" : "نام و نام خانوادگی را وارد کنید.");
    setError(
      phoneField,
      isValidIranianMobile(phoneNumber)
        ? ""
        : "شماره موبایل معتبر وارد کنید.",
    );
    setError(roleField, roleField.control.value ? "" : "یک نقش انتخاب کنید.");
    phoneField.control.value = phoneNumber;

    if (!fullName) nameField.control.focus();
    else if (!isValidIranianMobile(phoneNumber)) phoneField.control.focus();
    else if (!roleField.control.value) roleField.control.focus();

    return {
      isValid:
        Boolean(fullName) &&
        isValidIranianMobile(phoneNumber) &&
        Boolean(roleField.control.value),
      values: {
        fullName,
        phoneNumber,
        roleId: roleField.control.value,
        roleName: roleField.control.selectedOptions[0]?.textContent ?? "",
        status: statusField.control.value,
      },
    };
  };

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const { isValid, values } = validate();

    if (!isValid) return;

    submitButton.disabled = true;
    submitButton.textContent = "در حال ذخیره...";
    feedback.hidden = true;

    try {
      await onSubmit(values);
    } catch (error) {
      feedback.textContent = error.message ?? "ذخیره کاربر انجام نشد.";
      feedback.dataset.type = "error";
      feedback.hidden = false;
      submitButton.disabled = false;
      submitButton.textContent = user ? "ذخیره تغییرات" : "ایجاد کاربر";
    }
  });

  cancelButton.addEventListener("click", onCancel);
  actions.append(submitButton, cancelButton);
  form.append(
    feedback,
    nameField.field,
    phoneField.field,
    roleField.field,
    statusField.field,
    actions,
  );

  return form;
};
