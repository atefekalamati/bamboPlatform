export const Checklist = ({ items, initialValues = {}, onChange }) => {
  const fieldset = document.createElement("fieldset");
  const legend = document.createElement("legend");
  const list = document.createElement("div");
  const controls = new Map();

  fieldset.className = "checklist";
  legend.className = "checklist__legend";
  legend.textContent = "چک‌لیست تناسب پروژه";
  list.className = "checklist__items";

  items.forEach(({ id, label }) => {
    const wrapper = document.createElement("label");
    const input = document.createElement("input");
    const text = document.createElement("span");

    wrapper.className = "checklist__item";
    input.id = id;
    input.name = id;
    input.type = "checkbox";
    input.checked = Boolean(initialValues[id]);
    text.textContent = label;
    input.addEventListener("change", onChange);
    wrapper.append(input, text);
    list.append(wrapper);
    controls.set(id, { input, wrapper });
  });

  fieldset.append(legend, list);

  const getValues = () =>
    Object.fromEntries(
      [...controls.entries()].map(([id, control]) => [
        id,
        control.input.checked,
      ]),
    );

  const getErrors = () => {
    const errors = [];

    items.forEach(({ id, label }) => {
      const control = controls.get(id);
      const isInvalid = !control?.input.checked;

      control?.wrapper.classList.toggle("checklist__item--invalid", isInvalid);
      control?.input.setAttribute("aria-invalid", String(isInvalid));

      if (isInvalid) {
        errors.push({
        fieldId: id,
        message: `چک‌لیست «${label}» تکمیل نشده است.`,
        });
      }
    });

    return errors;
  };

  return { element: fieldset, getValues, getErrors };
};
