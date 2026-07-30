import {
  isValidIranianMobile,
  normalizePhoneNumber,
} from "../utils/phoneNumber.js";

const field = ({ id, label, readOnly = false }) => {
  const wrapper = document.createElement("div");
  const labelNode = document.createElement("label");
  const input = document.createElement("input");
  const error = document.createElement("p");
  wrapper.className = "form-field";
  labelNode.className = "form-field__label";
  labelNode.htmlFor = id;
  labelNode.textContent = label;
  input.id = id;
  input.className = "form-field__input";
  input.readOnly = readOnly;
  error.className = "form-field__error";
  error.id = `${id}-error`;
  input.setAttribute("aria-describedby", error.id);
  wrapper.append(labelNode, input, error);
  return { wrapper, input, error };
};

const setError = (target, message = "") => {
  target.error.textContent = message;
  target.input.setAttribute("aria-invalid", String(Boolean(message)));
};

const roleSelector = (roles, selectedRoleIds) => {
  const fieldset = document.createElement("fieldset");
  const legend = document.createElement("legend");
  const error = document.createElement("p");
  fieldset.className = "role-selector";
  legend.className = "form-field__label";
  legend.textContent = "نقش‌های کاربر";
  error.className = "form-field__error";
  fieldset.append(legend);
  roles
    .filter(({ isActive }) => isActive)
    .forEach((role) => {
      const label = document.createElement("label");
      const checkbox = document.createElement("input");
      const text = document.createElement("span");
      label.className = "role-selector__item";
      checkbox.type = "checkbox";
      checkbox.value = role.id;
      checkbox.checked = selectedRoleIds.has(role.id);
      text.textContent = role.displayName;
      label.append(checkbox, text);
      fieldset.append(label);
    });
  fieldset.append(error);
  return {
    fieldset,
    error,
    getRoleIds: () =>
      [...fieldset.querySelectorAll("input:checked")].map(({ value }) =>
        Number(value),
      ),
  };
};

export const UserForm = ({ user, roles, onSubmit, onCancel }) => {
  const form = document.createElement("form");
  const feedback = document.createElement("div");
  const name = field({
    id: "user-display-name",
    label: "نام و نام خانوادگی",
    readOnly: Boolean(user),
  });
  const mobile = field({
    id: "user-mobile",
    label: "شماره موبایل",
    readOnly: Boolean(user),
  });
  const selectedRoleIds = new Set(user?.roles.map(({ id }) => id) ?? []);
  const rolesField = roleSelector(roles, selectedRoleIds);
  const statusLabel = document.createElement("label");
  const status = document.createElement("select");
  const reason = field({ id: "status-reason", label: "دلیل تغییر وضعیت" });
  const actions = document.createElement("div");
  const submit = document.createElement("button");
  const cancel = document.createElement("button");

  form.className = "user-form";
  form.noValidate = true;
  feedback.className = "form-feedback";
  feedback.hidden = true;
  feedback.setAttribute("role", "alert");
  name.input.value = user?.displayName ?? "";
  mobile.input.value = user?.mobile ?? "";
  mobile.input.inputMode = "tel";
  statusLabel.className = "form-field";
  statusLabel.append(document.createElement("span"), status);
  statusLabel.firstElementChild.className = "form-field__label";
  statusLabel.firstElementChild.textContent = "وضعیت حساب";
  status.className = "form-field__input";
  status.append(new Option("فعال", "active"), new Option("غیرفعال", "inactive"));
  status.value = user?.isActive === false ? "inactive" : "active";
  reason.wrapper.hidden = !user;
  reason.input.placeholder = "مثال: پایان همکاری";
  actions.className = "form-actions";
  submit.className = "button button--primary";
  submit.type = "submit";
  submit.textContent = user ? "ذخیره تغییرات" : "ایجاد کاربر";
  cancel.className = "button button--ghost";
  cancel.type = "button";
  cancel.textContent = "انصراف";

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const displayName = name.input.value.trim();
    const normalizedMobile = user
      ? user.mobile
      : normalizePhoneNumber(mobile.input.value);
    const roleIds = rolesField.getRoleIds();
    const statusChanged =
      Boolean(user) && (status.value === "active") !== user.isActive;
    const reasonValue = reason.input.value.trim();
    const validName = user || (displayName.length >= 2 && displayName.length <= 120);
    const validMobile = user || isValidIranianMobile(normalizedMobile);
    const validReason = !statusChanged || reasonValue.length >= 2;

    setError(name, validName ? "" : "نام باید بین ۲ تا ۱۲۰ کاراکتر باشد.");
    setError(mobile, validMobile ? "" : "شماره موبایل معتبر وارد کنید.");
    rolesField.error.textContent = "";
    setError(
      reason,
      validReason ? "" : "برای تغییر وضعیت، دلیل را وارد کنید.",
    );
    mobile.input.value = normalizedMobile;
    if (!validName || !validMobile || !validReason) return;

    submit.disabled = true;
    submit.textContent = "در حال ذخیره...";
    feedback.hidden = true;
    try {
      await onSubmit({
        displayName,
        mobile: normalizedMobile,
        roleIds,
        isActive: status.value === "active",
        statusChanged,
        reason: reasonValue,
      });
    } catch (error) {
      feedback.textContent = error.message ?? "ذخیره کاربر انجام نشد.";
      feedback.dataset.type = "error";
      feedback.hidden = false;
      submit.disabled = false;
      submit.textContent = user ? "ذخیره تغییرات" : "ایجاد کاربر";
    }
  });

  cancel.addEventListener("click", onCancel);
  actions.append(submit, cancel);
  form.append(
    feedback,
    name.wrapper,
    mobile.wrapper,
    rolesField.fieldset,
    statusLabel,
    reason.wrapper,
    actions,
  );
  return form;
};
