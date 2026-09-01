import { sessionStore } from "../app/sessionStore.js";
import { EmptyState } from "../components/EmptyState.js";
import { Modal } from "../components/Modal.js";
import { Pagination } from "../components/Pagination.js";
import { PilotCard } from "../components/PilotCard.js";
import { PilotForm } from "../components/PilotForm.js";
import { pilotService } from "../services/pilotService.js";
import { debounce } from "../utils/debounce.js";
import { normalizeDigits } from "../utils/phoneNumber.js";

const PAGE_SIZE = 20;
const STATUS_OPTIONS = Object.freeze([
  { value: "", label: "همه وضعیت‌ها" },
  { value: "candidate", label: "نامزد پایلوت" },
  { value: "active", label: "فعال" },
  { value: "converted", label: "تبدیل‌شده" },
  { value: "closed", label: "بسته‌شده" },
]);

const element = (tag, className, text = "") => {
  const node = document.createElement(tag);
  node.className = className;
  node.textContent = text;
  return node;
};

export const PilotsPage = () => {
  const page = element("div", "page");
  const heading = element("header", "page-heading");
  const toolbar = element("div", "pilot-toolbar");
  const searchGroup = element("div", "filter-field");
  const statusGroup = element("div", "filter-field");
  const searchLabel = element("label", "filter-field__label", "جست‌وجو");
  const statusLabel = element("label", "filter-field__label", "وضعیت");
  const search = document.createElement("input");
  const status = document.createElement("select");
  const create = element("button", "button button--primary", "ایجاد پرونده");
  const region = element("section", "pilots-region");
  const canCreate = sessionStore
    .getCurrentUser()
    ?.permissions.includes("pilots.create");
  let pilots = [];
  let currentPage = 1;
  let totalPilots = 0;
  let totalPages = 1;
  let loadVersion = 0;

  heading.append(
    element("p", "page-heading__eyebrow", "مدیریت فرایند"),
    element("h1", "page-heading__title", "پرونده‌های پایلوت"),
    element(
      "p",
      "page-heading__description",
      "پرونده‌های واقعی پروژه و مرحله جاری آن‌ها را مشاهده و مدیریت کنید.",
    ),
  );
  searchLabel.htmlFor = "pilot-search";
  search.id = "pilot-search";
  search.className = "filter-field__control";
  search.type = "search";
  search.placeholder = "کد، نام پروژه یا نام سیستمی";
  statusLabel.htmlFor = "pilot-status";
  status.id = "pilot-status";
  status.className = "filter-field__control";
  STATUS_OPTIONS.forEach(({ value, label }) =>
    status.append(new Option(label, value)),
  );
  create.type = "button";
  create.hidden = !canCreate;
  searchGroup.append(searchLabel, search);
  statusGroup.append(statusLabel, status);
  toolbar.append(searchGroup, statusGroup, create);
  region.setAttribute("aria-live", "polite");

  const renderError = (message, retry) => {
    const state = element("div", "error-state");
    const button = element("button", "button button--primary", "تلاش مجدد");
    button.type = "button";
    button.addEventListener("click", retry);
    state.append(element("p", "error-state__message", message), button);
    region.replaceChildren(state);
  };

  const render = () => {
    const visible = pilots;
    if (!visible.length) {
      region.replaceChildren(
        EmptyState({
          title: "پرونده‌ای پیدا نشد",
          description: "فیلترها را تغییر دهید یا یک پرونده جدید ایجاد کنید.",
          actions: [
            {
              label: "پاک‌کردن فیلترها",
              onClick: () => {
                search.value = "";
                status.value = "";
                currentPage = 1;
                load();
                search.focus();
              },
            },
            ...(canCreate ? [{ label: "ایجاد پرونده", className: "button button--primary", onClick: () => create.click() }] : []),
          ],
        }),
      );
      return;
    }
    const list = element("ul", "pilot-list");
    visible.forEach((pilot) => list.append(PilotCard({ pilot })));
    region.replaceChildren(
      element("p", "results-count", `${totalPilots} پرونده`),
      list,
    );
    if (totalPages > 1) {
      region.append(
        Pagination({
          activePage: currentPage,
          totalPages,
          onPageChange: (pageNumber) => {
            currentPage = pageNumber;
            load();
          },
        }),
      );
    }
  };

  const load = async () => {
    const version = ++loadVersion;
    region.replaceChildren(
      element("p", "loading-state", "در حال دریافت پرونده‌ها..."),
    );
    try {
      const result = await pilotService.getPilotsPage({
        page: currentPage,
        page_size: PAGE_SIZE,
        q: normalizeDigits(search.value).trim(),
        status: status.value,
      });
      if (version !== loadVersion) return;
      pilots = result.items;
      totalPilots = result.total;
      totalPages = result.total_pages;
      currentPage = result.page;
      render();
    } catch (error) {
      if (version !== loadVersion) return;
      renderError(error.message ?? "دریافت پرونده‌ها انجام نشد.", load);
    }
  };

  const openCreateForm = () => {
    let modal;
    const form = PilotForm({
      onSubmit: async (values) => {
        const created = await pilotService.createPilot(values);
        modal.close();
        window.location.hash = `#/pilots/${created.id}`;
      },
      onCancel: () => modal.close(),
    });
    modal = Modal({
      title: "ایجاد پرونده پایلوت",
      content: form,
      triggerElement: create,
    });
  };

  const refresh = debounce(() => {
    currentPage = 1;
    load();
  }, 300);
  search.addEventListener("input", refresh);
  status.addEventListener("change", refresh);
  create.addEventListener("click", openCreateForm);
  page.append(heading, toolbar, region);
  load();
  return page;
};
