import { EmptyState } from "../components/EmptyState.js";
import { Pagination } from "../components/Pagination.js";
import { PilotCard } from "../components/PilotCard.js";
import { pilotService } from "../services/pilotService.js";
import { debounce } from "../utils/debounce.js";
import { normalizeDigits } from "../utils/phoneNumber.js";

const SEARCH_DELAY_MS = 350;
const DEFAULT_PAGE_SIZE = 20;

const STATUS_OPTIONS = Object.freeze([
  { value: "", label: "همه وضعیت‌ها" },
  { value: "candidate", label: "نامزد پایلوت" },
  { value: "awaiting_documents", label: "در انتظار مدارک" },
  { value: "ready_for_capture", label: "آماده برداشت" },
  { value: "operations", label: "عملیات" },
  { value: "tour_building", label: "در حال ساخت تور" },
  { value: "ready_to_view", label: "آماده مشاهده" },
  { value: "evaluation", label: "در ارزیابی" },
  { value: "proposal_sent", label: "پیشنهاد ارسال‌شده" },
  { value: "converted", label: "تبدیل‌شده" },
  { value: "closed", label: "بسته‌شده" },
]);

const createElement = (tagName, className, textContent = "") => {
  const element = document.createElement(tagName);

  element.className = className;
  element.textContent = textContent;

  return element;
};

const createPageHeading = () => {
  const heading = createElement("header", "page-heading");
  const eyebrow = createElement("p", "page-heading__eyebrow", "مدیریت فرایند");
  const title = createElement(
    "h1",
    "page-heading__title",
    "پرونده‌های پایلوت",
  );
  const description = createElement(
    "p",
    "page-heading__description",
    "وضعیت، مرحله جاری، مسئول و SLA پرونده‌های پایلوت را مشاهده کنید.",
  );

  heading.append(eyebrow, title, description);

  return heading;
};

const appendStatusOptions = (select) => {
  STATUS_OPTIONS.forEach(({ value, label }) => {
    const option = document.createElement("option");
    option.value = value;
    option.textContent = label;
    select.append(option);
  });
};

export const PilotsPage = () => {
  const page = createElement("div", "page");
  const toolbar = createElement("div", "pilot-toolbar");
  const searchGroup = createElement("div", "filter-field");
  const searchLabel = createElement("label", "filter-field__label", "جست‌وجو");
  const searchInput = document.createElement("input");
  const statusGroup = createElement("div", "filter-field");
  const statusLabel = createElement("label", "filter-field__label", "وضعیت");
  const statusSelect = document.createElement("select");
  const resultsRegion = createElement("section", "pilots-region");
  let currentPage = 1;

  searchLabel.htmlFor = "pilot-search";
  searchInput.id = "pilot-search";
  searchInput.className = "filter-field__control";
  searchInput.type = "search";
  searchInput.placeholder = "کد، پروژه یا مالک";
  searchInput.autocomplete = "off";
  statusLabel.htmlFor = "pilot-status";
  statusSelect.id = "pilot-status";
  statusSelect.className = "filter-field__control";
  appendStatusOptions(statusSelect);
  searchGroup.append(searchLabel, searchInput);
  statusGroup.append(statusLabel, statusSelect);
  toolbar.append(searchGroup, statusGroup);
  resultsRegion.setAttribute("aria-live", "polite");
  resultsRegion.setAttribute("aria-busy", "true");

  const renderLoading = () => {
    resultsRegion.setAttribute("aria-busy", "true");
    resultsRegion.replaceChildren(
      createElement("p", "loading-state", "در حال دریافت پرونده‌ها..."),
    );
  };

  const renderError = () => {
    const state = createElement("div", "error-state");
    const message = createElement(
      "p",
      "error-state__message",
      "دریافت فهرست پرونده‌ها انجام نشد.",
    );
    const retryButton = createElement(
      "button",
      "button button--primary",
      "تلاش مجدد",
    );

    retryButton.type = "button";
    retryButton.addEventListener("click", loadPilots);
    state.append(message, retryButton);
    resultsRegion.replaceChildren(state);
  };

  const renderPilots = ({ items, page: activePage, totalItems, totalPages }) => {
    if (!items.length) {
      resultsRegion.replaceChildren(
        EmptyState({
          title: "پرونده‌ای پیدا نشد",
          description: "فیلترها را تغییر دهید و دوباره تلاش کنید.",
        }),
      );
      return;
    }

    const count = createElement("p", "results-count", `${totalItems} پرونده`);
    const list = createElement("ul", "pilot-list");
    items.forEach((pilot) => list.append(PilotCard({ pilot })));
    resultsRegion.replaceChildren(count, list);

    if (totalPages > 1) {
      resultsRegion.append(
        Pagination({
          activePage,
          totalPages,
          onPageChange: (selectedPage) => {
            currentPage = selectedPage;
            loadPilots();
          },
        }),
      );
    }
  };

  const loadPilots = async () => {
    renderLoading();

    try {
      const response = await pilotService.getPilots({
        search: normalizeDigits(searchInput.value),
        status: statusSelect.value,
        page: currentPage,
        pageSize: DEFAULT_PAGE_SIZE,
      });
      renderPilots(response.data);
    } catch {
      renderError();
    } finally {
      resultsRegion.setAttribute("aria-busy", "false");
    }
  };

  const refreshFilters = () => {
    currentPage = 1;
    loadPilots();
  };

  searchInput.addEventListener(
    "input",
    debounce(refreshFilters, SEARCH_DELAY_MS),
  );
  statusSelect.addEventListener("change", refreshFilters);

  page.append(createPageHeading(), toolbar, resultsRegion);
  loadPilots();

  return page;
};

