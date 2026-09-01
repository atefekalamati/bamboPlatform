import { contactsSummaryFromConfirmation } from "../features/stages/stageFour.js";
import { formatIranDateTimeLocalValue } from "../utils/jalaliDateTime.js";

const CONTACTS_SUMMARY_KEY = "contactsSummaryConfirmed";

const CHECKLIST_ITEMS = Object.freeze([
  {
    key: CONTACTS_SUMMARY_KEY,
    label: "اطلاعات افراد و راه‌های ارتباطی بررسی و ثبت شد.",
  },
  {
    key: "mainProjectRegistered",
    label: "پروژه با نام استاندارد ایجاد شد.",
  },
  {
    key: "floorOrderConfirmed",
    label: "طبقات به ترتیب صحیح تعریف شدند.",
  },
  {
    key: "planConnectionsRegistered",
    label: "پلان صحیح هر طبقه بارگذاری شد.",
  },
  {
    key: "typicalFloorsIdentified",
    label: "طبقات تیپ و غیرتیپ مشخص شدند.",
  },
  {
    key: "startPointRegistered",
    label: "نقطه شروع پیشنهادی ثبت شد.",
  },
  {
    key: "expertAccessTested",
    label: "دسترسی کارشناس فعال شد.",
  },
  {
    key: "mainAppDisplayTested",
    label: "نمایش پروژه در اپلیکیشن آزمایش شد.",
  },
  {
    key: "readyForCapture",
    label: "پروژه آماده برداشت است.",
  },
]);

const field = ({ id, label, value = "", disabled, type = "textarea" }) => {
  const wrapper = document.createElement("div");
  const labelNode = document.createElement("label");
  const control = document.createElement(type);
  wrapper.className = "stage-form__field";
  labelNode.className = "stage-form__label";
  labelNode.htmlFor = id;
  labelNode.textContent = label;
  control.id = id;
  control.className = "stage-form__control";
  control.value = value ?? "";
  control.disabled = disabled;
  wrapper.append(labelNode, control);
  return { wrapper, control };
};

const toDateTimeLocalValue = formatIranDateTimeLocalValue;

export const StageFourForm = ({ initialData, disabled, onChange }) => {
  const values = initialData ?? {};
  const form = document.createElement("form");
  const information = document.createElement("fieldset");
  const informationLegend = document.createElement("legend");
  const grid = document.createElement("div");
  const progressStatus = field({
    id: "stage4-progress-status",
    label: "وضعیت پیشرفت راه‌اندازی",
    value: values.progressStatus,
    disabled,
    type: "input",
  });
  const limitation = field({
    id: "stage4-limitation",
    label: "محدودیت‌ها",
    value: values.limitation,
    disabled,
  });
  const ambiguity = field({
    id: "stage4-ambiguity",
    label: "ابهام‌ها یا موارد نیازمند پیگیری",
    value: values.ambiguity,
    disabled,
  });
  const referredAt = field({
    id: "stage4-referred-at",
    label: "تاریخ و ساعت ارجاع",
    value: toDateTimeLocalValue(values.referredAt),
    disabled,
    type: "input",
  });
  const checklist = document.createElement("fieldset");
  const checklistLegend = document.createElement("legend");
  const checklistItems = new Map();

  form.className = "stage-form";
  information.className = "stage-form__section";
  informationLegend.className = "stage-form__legend";
  informationLegend.textContent = "اطلاعات راه‌اندازی F02";
  grid.className = "stage-form__grid";
  [
    progressStatus,
    limitation,
    ambiguity,
    referredAt,
  ].forEach(({ control }) => control.addEventListener("input", onChange));
  referredAt.control.type = "datetime-local";
  grid.append(
    progressStatus.wrapper,
    limitation.wrapper,
    ambiguity.wrapper,
    referredAt.wrapper,
  );
  information.append(informationLegend, grid);

  checklist.className = "checklist";
  checklistLegend.className = "checklist__legend";
  checklistLegend.textContent = "چک‌لیست آمادگی فنی G2";
  checklist.append(checklistLegend);
  CHECKLIST_ITEMS.forEach(({ key, label }) => {
    const item = document.createElement("label");
    const checkbox = document.createElement("input");
    const text = document.createElement("span");
    item.className = "checklist__item";
    checkbox.type = "checkbox";
    checkbox.checked = key === CONTACTS_SUMMARY_KEY
      ? Boolean(values.contactsSummary)
      : Boolean(values[key]);
    checkbox.disabled = disabled;
    checkbox.addEventListener("change", () => {
      item.classList.remove("checklist__item--invalid");
      onChange();
    });
    text.textContent = label;
    item.append(checkbox, text);
    checklist.append(item);
    checklistItems.set(key, { checkbox, item });
  });
  form.append(information, checklist);

  const getData = () => ({
    ...values,
    informationPackage: "",
    contactsSummary: contactsSummaryFromConfirmation(
      checklistItems.get(CONTACTS_SUMMARY_KEY)?.checkbox.checked,
    ),
    progressStatus: progressStatus.control.value.trim(),
    limitation: limitation.control.value.trim(),
    ambiguity: ambiguity.control.value.trim(),
    referredAt: referredAt.control.value || null,
    ...Object.fromEntries(
      [...checklistItems]
        .filter(([key]) => key !== CONTACTS_SUMMARY_KEY)
        .map(([key, { checkbox }]) => [key, checkbox.checked]),
    ),
  });

  const validate = () => {
    const errors = [];
    checklistItems.forEach(({ checkbox, item }, key) => {
      item.classList.toggle("checklist__item--invalid", !checkbox.checked);
      if (!checkbox.checked) errors.push({ field: key });
    });
    return errors;
  };

  return { element: form, getData, validate };
};
