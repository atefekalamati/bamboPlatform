const CHECKLIST_ITEMS = Object.freeze([
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

export const StageFourForm = ({ initialData, disabled, onChange }) => {
  const values = initialData ?? {};
  const form = document.createElement("form");
  const information = document.createElement("fieldset");
  const informationLegend = document.createElement("legend");
  const grid = document.createElement("div");
  const informationPackage = field({
    id: "stage4-information-package",
    label: "بسته اطلاعاتی پروژه",
    value: values.informationPackage,
    disabled,
  });
  const contactsSummary = field({
    id: "stage4-contacts-summary",
    label: "خلاصه افراد و راه‌های ارتباطی",
    value: values.contactsSummary,
    disabled,
  });
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
  const checklist = document.createElement("fieldset");
  const checklistLegend = document.createElement("legend");
  const checklistItems = new Map();

  form.className = "stage-form";
  information.className = "stage-form__section";
  informationLegend.className = "stage-form__legend";
  informationLegend.textContent = "اطلاعات راه‌اندازی F02";
  grid.className = "stage-form__grid";
  [
    informationPackage,
    contactsSummary,
    progressStatus,
    limitation,
    ambiguity,
  ].forEach(({ control }) => control.addEventListener("input", onChange));
  grid.append(
    informationPackage.wrapper,
    contactsSummary.wrapper,
    progressStatus.wrapper,
    limitation.wrapper,
    ambiguity.wrapper,
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
    checkbox.checked = Boolean(values[key]);
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
    informationPackage: informationPackage.control.value.trim(),
    contactsSummary: contactsSummary.control.value.trim(),
    progressStatus: progressStatus.control.value.trim(),
    limitation: limitation.control.value.trim(),
    ambiguity: ambiguity.control.value.trim(),
    ...Object.fromEntries(
      [...checklistItems].map(([key, { checkbox }]) => [
        key,
        checkbox.checked,
      ]),
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
