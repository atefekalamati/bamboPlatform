const CHECKS = Object.freeze([
  { key: "projectActive", label: "پروژه فعال است." },
  { key: "imagingValue", label: "تصویربرداری برای پروژه ارزش ایجاد می‌کند." },
  { key: "remoteViewingNeed", label: "نیاز به مشاهده غیرحضوری وجود دارد.", required: false },
  { key: "accessPossible", label: "دسترسی ایمن و هماهنگ به پروژه ممکن است." },
  { key: "dwgAvailable", label: "فایل DWG قابل دریافت است." },
  { key: "notDemoOnly", label: "پروژه صرفاً نمایش آزمایشی نیست." },
  { key: "continuedCapacity", label: "ظرفیت ادامه همکاری وجود دارد." },
]);

const EMPTY_F01 = Object.freeze({
  projectActive: false,
  imagingValue: false,
  remoteViewingNeed: false,
  accessPossible: false,
  dwgAvailable: false,
  continuedCapacity: false,
  notDemoOnly: false,
  introductionCompleted: false,
  imagingAccepted: false,
  dwgAccepted: false,
  feedbackAccepted: false,
  result: "complete_information",
});

export const StageOneForm = ({ initialData, project, disabled, onChange }) => {
  const form = document.createElement("form");
  const projectSection = document.createElement("section");
  const checklist = document.createElement("fieldset");
  const legend = document.createElement("legend");
  const resultLabel = document.createElement("label");
  const result = document.createElement("select");
  const resultError = document.createElement("p");
  const values = { ...EMPTY_F01, ...initialData };
  const checkboxes = new Map();
  const summary = document.createElement("dl");

  form.className = "stage-form";
  projectSection.className = "stage-form__section";
  summary.className = "stage-project-summary";
  [
    ["مالک", project.owner.name],
    ["تصمیم‌گیرنده", project.owner.decisionMakerName],
    ["پروژه", project.name],
    ["آدرس", project.address],
  ].forEach(([label, value]) => {
    const item = document.createElement("div");
    const term = document.createElement("dt");
    const description = document.createElement("dd");
    term.textContent = label;
    description.textContent = value;
    item.append(term, description);
    summary.append(item);
  });
  const projectTitle = document.createElement("h2");
  projectTitle.className = "stage-form__legend";
  projectTitle.textContent = "اطلاعات ثبت‌شده پروژه";
  projectSection.append(projectTitle, summary);
  checklist.className = "checklist";
  legend.className = "checklist__legend";
  legend.textContent = "چک‌لیست تناسب پروژه";
  checklist.append(legend);

  CHECKS.forEach(({ key, label, required = true }) => {
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
    text.textContent = `${label}${required ? " *" : ""}`;
    item.append(checkbox, text);
    checklist.append(item);
    checkboxes.set(key, { checkbox, item, required });
  });

  resultLabel.className = "stage-form__field";
  resultLabel.append(document.createElement("span"), result, resultError);
  resultLabel.firstElementChild.className = "stage-form__label";
  resultLabel.firstElementChild.textContent = "نتیجه ارزیابی";
  result.className = "stage-form__control";
  result.disabled = disabled;
  result.append(
    new Option("نیازمند تکمیل اطلاعات", "complete_information"),
    new Option("تأیید اولیه", "approved"),
    new Option("ردشده", "rejected"),
    new Option("ارجاع‌شده", "referred"),
  );
  result.value = values.result;
  result.addEventListener("change", onChange);
  resultError.className = "stage-form__error";
  checklist.append(resultLabel);
  form.append(projectSection, checklist);

  const getData = () => ({
    ...values,
    ...Object.fromEntries(
      [...checkboxes].map(([key, { checkbox }]) => [key, checkbox.checked]),
    ),
    result: result.value,
  });

  const validate = () => {
    const errors = [];
    checkboxes.forEach(({ checkbox, item, required }, key) => {
      const invalid = required && !checkbox.checked;
      item.classList.toggle("checklist__item--invalid", invalid);
      if (invalid) errors.push({ field: `checklist.${key}` });
    });
    return errors;
  };

  return { element: form, getData, validate };
};
