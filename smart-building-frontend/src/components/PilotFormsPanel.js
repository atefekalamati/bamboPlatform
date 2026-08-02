import { formService } from "../services/formService.js";
import { formatPersianDate } from "../utils/dateFormatter.js";

const element = (tag, className = "", text = "") => {
  const node = document.createElement(tag);
  node.className = className;
  node.textContent = text;
  return node;
};

const valueText = (value) => {
  if (value === true) return "☑";
  if (value === false) return "☐";
  if (value === null || value === undefined || value === "") return "—";
  if (Array.isArray(value)) return value.length ? `${value.length} مورد` : "—";
  if (typeof value === "object") return "";
  return String(value);
};

const renderPreviewSection = (title, value) => {
  const section = element("section", "forms-preview__section");
  section.append(element("h4", "forms-preview__section-title", title));

  if (Array.isArray(value)) {
    if (!value.length) {
      section.append(element("p", "muted-text", "داده‌ای ثبت نشده است."));
      return section;
    }
    const table = element("table", "forms-preview__table");
    const headers = Object.keys(value[0]);
    const head = document.createElement("thead");
    const headRow = document.createElement("tr");
    headers.forEach((header) => headRow.append(element("th", "", header)));
    head.append(headRow);
    const body = document.createElement("tbody");
    value.forEach((row) => {
      const tr = document.createElement("tr");
      headers.forEach((header) => tr.append(element("td", "", valueText(row[header]))));
      body.append(tr);
    });
    table.append(head, body);
    section.append(table);
    return section;
  }

  const list = element("dl", "forms-preview__grid");
  Object.entries(value ?? {}).forEach(([key, item]) => {
    list.append(element("dt", "", key), element("dd", "", valueText(item)));
  });
  section.append(list);
  return section;
};

const openPrintWindow = (html) => {
  const popup = window.open("", "_blank", "noopener,noreferrer");
  if (!popup) throw new Error("مرورگر اجازه بازشدن پنجره چاپ را نداد.");
  popup.document.open();
  popup.document.write(html);
  popup.document.close();
  popup.focus();
};

const downloadBlob = ({ blob, filename }) => {
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.append(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
};

export const PilotFormsPanel = ({ pilotId }) => {
  const panel = element("section", "project-forms card");
  const title = element("h2", "section-title", "فرم‌های پروژه");
  const status = element("p", "muted-text", "در حال دریافت فرم‌ها...");
  const preview = element("div", "forms-preview");

  const showError = (error) => {
    preview.replaceChildren(
      element("p", "error-state__message", error.message ?? "عملیات فرم انجام نشد."),
    );
  };

  const renderPreview = async (href) => {
    preview.replaceChildren(element("p", "muted-text", "در حال دریافت پیش‌نمایش..."));
    const documentData = await formService.getPreview(href);
    const header = element("div", "forms-preview__header");
    header.append(
      element("h3", "", `${documentData.form_code} — ${documentData.title}`),
      element(
        "span",
        documentData.is_complete ? "status-badge" : "status-badge status-badge--warning",
        documentData.is_complete ? "کامل" : "اطلاعات ناقص",
      ),
    );
    const sections = Object.entries(documentData.data).map(([section, value]) =>
      renderPreviewSection(section, value),
    );
    const missing = element("div", "forms-preview__missing");
    if (documentData.missing_fields?.length) {
      missing.append(element("h4", "", "فیلدهای ناقص"));
      const list = element("ul", "");
      documentData.missing_fields.forEach((item) =>
        list.append(element("li", "", `${item.label} (${item.field})`)),
      );
      missing.append(list);
    }
    preview.replaceChildren(header, ...sections, missing);
  };

  const renderActions = (instance) => {
    const actions = element("div", "form-actions");
    const view = element("button", "button button--ghost", "مشاهده");
    const print = element("button", "button button--ghost", "چاپ");
    const pdf = element("button", "button button--ghost", "PDF");
    view.type = print.type = pdf.type = "button";
    view.disabled = !instance.href;
    print.disabled = !instance.print_href;
    pdf.disabled = !instance.pdf_href;
    view.addEventListener("click", () => renderPreview(instance.href).catch(showError));
    print.addEventListener("click", async () => {
      try {
        openPrintWindow(await formService.getPrintHtml(instance.print_href));
      } catch (error) {
        showError(error);
      }
    });
    pdf.addEventListener("click", async () => {
      try {
        downloadBlob(await formService.downloadPdf(instance.pdf_href));
      } catch (error) {
        showError(error);
      }
    });
    actions.append(view, print, pdf);
    return actions;
  };

  const renderForms = (forms) => {
    const table = element("table", "project-forms__table");
    const head = document.createElement("thead");
    const headRow = document.createElement("tr");
    ["فرم", "وضعیت اطلاعات", "تعداد نسخه قابل چاپ", "آخرین تغییر", "عملیات"].forEach(
      (header) => headRow.append(element("th", "", header)),
    );
    head.append(headRow);
    const body = document.createElement("tbody");

    forms.forEach((form) => {
      const instances = form.instances?.length ? form.instances : [];
      if (instances.length <= 1) {
        const instance = instances[0] ?? {};
        const tr = document.createElement("tr");
        tr.append(
          element("td", "", `${form.form_code} — ${form.title}`),
          element("td", "", form.status_label),
          element("td", "", String(form.printable_count)),
          element("td", "", formatPersianDate(form.last_changed)),
        );
        const actions = document.createElement("td");
        actions.append(renderActions(instance));
        tr.append(actions);
        body.append(tr);
        return;
      }

      instances.forEach((instance, index) => {
        const tr = document.createElement("tr");
        tr.append(
          element("td", "", index === 0 ? `${form.form_code} — ${form.title}` : instance.title),
          element("td", "", instance.is_complete ? "کامل" : "ناقص"),
          element("td", "", "۱"),
          element("td", "", formatPersianDate(instance.last_changed)),
        );
        const actions = document.createElement("td");
        actions.append(renderActions(instance));
        tr.append(actions);
        body.append(tr);
      });
    });

    table.append(head, body);
    panel.replaceChildren(title, table, preview);
  };

  const load = async () => {
    try {
      renderForms(await formService.listForms(pilotId));
    } catch (error) {
      status.textContent = error.message ?? "دریافت فرم‌های پروژه انجام نشد.";
      panel.replaceChildren(title, status);
    }
  };

  panel.append(title, status);
  load();
  return panel;
};
