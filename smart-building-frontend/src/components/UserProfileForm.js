import { buildUserNamePatch } from "../features/users/userProfile.js";

const field = (id, label) => {
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
  input.autocomplete = "name";
  error.className = "form-field__error";
  error.id = `${id}-error`;
  input.setAttribute("aria-describedby", error.id);
  wrapper.append(labelNode, input, error);
  return { wrapper, input, error };
};

export const UserProfileForm = ({ user, onSubmit, onCancel }) => {
  const form = document.createElement("form");
  const feedback = document.createElement("p");
  const name = field("profile-display-name", "نام و نام خانوادگی");
  const actions = document.createElement("div");
  const submit = document.createElement("button");
  const cancel = document.createElement("button");

  form.className = "user-form";
  form.noValidate = true;
  feedback.className = "form-feedback";
  feedback.hidden = true;
  feedback.setAttribute("role", "alert");
  name.input.value = user.displayName ?? user.display_name ?? "";
  actions.className = "form-actions";
  submit.className = "button button--primary";
  submit.type = "submit";
  submit.textContent = "ذخیره نام";
  cancel.className = "button button--ghost";
  cancel.type = "button";
  cancel.textContent = "انصراف";

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const { payload, errors } = buildUserNamePatch({
      currentDisplayName: user.displayName ?? user.display_name ?? "",
      displayName: name.input.value,
    });
    name.error.textContent = errors.displayName ?? "";
    name.input.setAttribute("aria-invalid", String(Boolean(errors.displayName)));
    feedback.textContent = errors.form ?? "";
    feedback.hidden = !errors.form;
    if (Object.keys(errors).length) return;

    submit.disabled = true;
    feedback.hidden = true;
    try {
      await onSubmit(payload);
    } catch (error) {
      feedback.textContent = error.message ?? "ویرایش نام انجام نشد.";
      feedback.hidden = false;
      submit.disabled = false;
    }
  });

  cancel.addEventListener("click", onCancel);
  actions.append(submit, cancel);
  form.append(feedback, name.wrapper, actions);
  return form;
};
