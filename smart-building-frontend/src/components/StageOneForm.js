import { Checklist } from "./Checklist.js";
import {
  isValidIranianMobile,
  normalizePhoneNumber,
} from "../utils/phoneNumber.js";

const FIELD_GROUPS = Object.freeze([
  {
    title: "اطلاعات مالک و پروژه",
    fields: [
      { id: "ownerName", label: "نام مالک یا شرکت", required: true },
      { id: "decisionMakerName", label: "نام تصمیم‌گیرنده", required: true },
      { id: "decisionMakerRole", label: "سمت تصمیم‌گیرنده", required: true },
      {
        id: "phoneNumber",
        label: "شماره تماس",
        required: true,
        inputMode: "tel",
      },
      { id: "projectName", label: "نام پروژه", required: true },
      {
        id: "floorCount",
        label: "تعداد طبقات",
        required: true,
        type: "number",
        min: "1",
      },
      { id: "address", label: "نشانی", required: true, multiline: true },
      { id: "projectPhase", label: "مرحله پیشرفت", required: true },
    ],
  },
  {
    title: "ارزش و مسئولیت",
    fields: [
      {
        id: "customerNeed",
        label: "نیاز یا مسئله مشتری",
        multiline: true,
      },
      {
        id: "expectedValue",
        label: "ارزش مورد انتظار",
        multiline: true,
      },
      { id: "caseOwner", label: "مسئول پرونده", required: true },
      { id: "deadline", label: "مهلت", type: "date", required: true },
    ],
  },
]);

const CHECKLIST_ITEMS = Object.freeze([
  { id: "isProjectActive", label: "پروژه فعال است." },
  {
    id: "hasCaptureValue",
    label: "مرحله پروژه ارزش تصویربرداری دارد.",
  },
  {
    id: "isDecisionMakerAvailable",
    label: "مالک یا تصمیم‌گیرنده در دسترس است.",
  },
  { id: "hasSafeAccess", label: "ورود ایمن و هماهنگ ممکن است." },
  { id: "canReceiveDwg", label: "DWG طبقات قابل دریافت است." },
  { id: "isRealPilot", label: "پروژه صرفاً نمایش صوری نیست." },
  { id: "hasContinuationCapacity", label: "ظرفیت ادامه همکاری دارد." },
]);

const createField = (config, initialValue, onChange) => {
  const wrapper = document.createElement("div");
  const label = document.createElement("label");
  const control = document.createElement(
    config.multiline ? "textarea" : "input",
  );
  const error = document.createElement("p");

  wrapper.className = "stage-form__field";
  label.className = "stage-form__label";
  label.htmlFor = config.id;
  label.textContent = `${config.label}${config.required ? " *" : ""}`;
  control.id = config.id;
  control.name = config.id;
  control.className = "stage-form__control";
  control.value = initialValue ?? "";
  control.required = Boolean(config.required);

  if (!config.multiline) {
    control.type = config.type ?? "text";
    if (config.inputMode) control.inputMode = config.inputMode;
    if (config.min) control.min = config.min;
  }

  error.id = `${config.id}-error`;
  error.className = "stage-form__error";
  control.setAttribute("aria-describedby", error.id);
  control.addEventListener("input", onChange);
  wrapper.append(label, control, error);

  return { config, wrapper, control, error };
};

const validateField = ({ config, control }) => {
  const value = control.value.trim();

  if (config.required && !value) return `${config.label} الزامی است.`;
  if (config.id === "phoneNumber" && !isValidIranianMobile(value)) {
    return "شماره تماس معتبر وارد کنید.";
  }
  if (config.id === "floorCount" && Number(value) < 1) {
    return "تعداد طبقات باید حداقل یک باشد.";
  }

  return "";
};

export const StageOneForm = ({ initialData = {}, onChange }) => {
  const form = document.createElement("form");
  const controls = new Map();

  form.className = "stage-form";
  form.noValidate = true;

  FIELD_GROUPS.forEach(({ title, fields }) => {
    const section = document.createElement("fieldset");
    const legend = document.createElement("legend");
    const grid = document.createElement("div");

    section.className = "stage-form__section";
    legend.className = "stage-form__legend";
    legend.textContent = title;
    grid.className = "stage-form__grid";

    fields.forEach((config) => {
      const field = createField(config, initialData.form?.[config.id], onChange);
      controls.set(config.id, field);
      grid.append(field.wrapper);
    });

    section.append(legend, grid);
    form.append(section);
  });

  const checklist = Checklist({
    items: CHECKLIST_ITEMS,
    initialValues: initialData.checklist,
    onChange,
  });
  form.append(checklist.element);

  const getData = () => {
    const values = Object.fromEntries(
      [...controls.entries()].map(([id, field]) => {
        const value =
          id === "phoneNumber"
            ? normalizePhoneNumber(field.control.value)
            : field.control.value.trim();

        return [id, value];
      }),
    );

    return { form: values, checklist: checklist.getValues() };
  };

  const validate = () => {
    const errors = [];

    controls.forEach((field, id) => {
      const message = validateField(field);
      field.error.textContent = message;
      field.control.setAttribute("aria-invalid", String(Boolean(message)));
      if (message) errors.push({ fieldId: id, message });
    });

    errors.push(...checklist.getErrors());

    return errors;
  };

  return { element: form, getData, validate };
};
