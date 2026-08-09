import { formService } from "../services/formService.js";
import { formatPersianDateTime } from "../utils/dateFormatter.js";

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

const appendValue = (container, value) => {
  if (typeof value === "boolean") {
    const item = element("span", "official-form__check");
    item.append(
      element("span", `official-form__checkbox${value ? " is-checked" : ""}`, value ? "✓" : ""),
    );
    container.append(item);
    return;
  }
  container.append(document.createTextNode(valueText(value)));
};

const renderOfficialTable = (rows) => {
  const wrapper = element("div", "official-form__table-wrap");
  if (!rows.length) {
    wrapper.append(element("p", "official-form__empty", "داده‌ای ثبت نشده است."));
    return wrapper;
  }
  const table = element("table", "official-form__table");
  const headers = Object.keys(rows[0]);
  const head = document.createElement("thead");
  const headRow = document.createElement("tr");
  headers.forEach((header) => headRow.append(element("th", "", header)));
  head.append(headRow);
  const body = document.createElement("tbody");
  rows.forEach((row) => {
    const tr = document.createElement("tr");
    headers.forEach((header) => {
      const cell = document.createElement("td");
      appendValue(cell, row[header]);
      tr.append(cell);
    });
    body.append(tr);
  });
  table.append(head, body);
  wrapper.append(table);
  return wrapper;
};

const renderPreviewSection = (title, value) => {
  const section = element("section", "official-form__section");
  section.append(element("h4", "official-form__section-title", title));

  if (Array.isArray(value)) {
    section.append(renderOfficialTable(value));
    return section;
  }

  const list = element("dl", "official-form__fields");
  Object.entries(value ?? {}).forEach(([key, item]) => {
    if (Array.isArray(item)) {
      const group = element("div", "official-form__nested");
      group.append(element("h5", "", key), renderOfficialTable(item));
      list.append(group);
      return;
    }
    const isSignature = ["امضا", "تأیید", "ثبت‌کننده", "مسئول اقدام اصلاحی"].some(
      (token) => key.includes(token),
    );
    const isWide = ["نشانی", "نیاز", "ارزش", "محدودیت", "ابهام", "توضیح", "علت", "اقدام", "شاهد", "درس", "افراد"].some(
      (token) => key.includes(token),
    );
    const row = element(
      "div",
      [
        "official-form__field",
        typeof item === "boolean" ? "official-form__field--check" : "",
        isSignature && typeof item !== "boolean" ? "official-form__field--signature" : "",
        isWide ? "official-form__field--wide" : "",
      ].filter(Boolean).join(" "),
    );
    row.append(element("dt", "", key));
    const valueNode = document.createElement("dd");
    appendValue(valueNode, item);
    row.append(valueNode);
    list.append(row);
  });
  section.append(list);
  return section;
};

const renderOfficialDocument = (documentData) => {
  const paper = element("article", `official-form official-form--${documentData.form_code.toLowerCase()}`);
  const header = element("header", "official-form__header");
  const identity = element("div", "official-form__identity");
  identity.append(
    element("strong", "official-form__label", `فرم ${documentData.form_code}${documentData.form_code === "F05" ? " – فقط برای موارد استثنایی" : ""}`),
    element("h3", "official-form__title", documentData.title),
  );
  const meta = element("dl", "official-form__meta");
  [["کد سند", documentData.document_code], ["نسخه", documentData.version]].forEach(([key, value]) => {
    const row = element("div");
    row.append(element("dt", "", key), element("dd", "", value));
    meta.append(row);
  });
  header.append(identity, meta);
  paper.append(header);
  Object.entries(documentData.data).forEach(([section, value]) => {
    paper.append(renderPreviewSection(section, value));
  });
  return paper;
};

const createPrintWindow = (message = "در حال آماده‌سازی فرم برای چاپ…") => {
  const popup = window.open("", "_blank");
  if (!popup) throw new Error("مرورگر اجازه بازشدن پنجره چاپ را نداد.");
  popup.document.open();
  popup.document.write(`<!doctype html><html lang="fa" dir="rtl"><head><meta charset="utf-8"><title>آماده‌سازی فرم</title></head><body style="font-family:Tahoma,sans-serif;padding:2rem;text-align:center">${message}</body></html>`);
  popup.document.close();
  return popup;
};

const renderPrintWindow = (popup, html) => {
  if (popup.closed) throw new Error("پنجره چاپ پیش از آماده‌شدن فرم بسته شد.");
  popup.document.open();
  popup.document.write(html);
  popup.document.close();
  popup.focus();
  window.setTimeout(() => {
    if (!popup.closed) popup.print();
  }, 250);
};

const downloadBlob = ({ blob, filename }) => {
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.append(link);
  link.click();
  link.remove();
  window.setTimeout(() => URL.revokeObjectURL(url), 1000);
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
    const header = element("div", "forms-preview__header screen-only");
    header.append(
      element("h3", "", `${documentData.form_code} — ${documentData.title}`),
      element(
        "span",
        documentData.is_complete ? "status-badge" : "status-badge status-badge--warning",
        documentData.is_complete ? "کامل" : "اطلاعات ناقص",
      ),
    );
    preview.replaceChildren(header, renderOfficialDocument(documentData));
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
      let popup;
      try {
        popup = createPrintWindow();
        const html = await formService.getPrintHtml(instance.print_href);
        renderPrintWindow(popup, html);
      } catch (error) {
        if (popup && !popup.closed) popup.close();
        showError(error);
      }
    });
    pdf.addEventListener("click", async () => {
      let popup;
      try {
        popup = createPrintWindow("در حال ساخت فایل PDF…");
        const file = await formService.downloadPdf(instance.pdf_href);
        if (!popup.closed) popup.close();
        downloadBlob(file);
      } catch (pdfError) {
        if (!popup) {
          showError(pdfError);
          return;
        }
        try {
          const html = await formService.getPrintHtml(instance.print_href);
          renderPrintWindow(popup, html);
        } catch (printError) {
          if (popup && !popup.closed) popup.close();
          showError(printError ?? pdfError);
        }
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
          element("td", "", formatPersianDateTime(form.last_changed)),
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
          element("td", "", formatPersianDateTime(instance.last_changed)),
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
