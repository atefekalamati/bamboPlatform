import { EmptyState } from "../components/EmptyState.js";
import { Modal } from "../components/Modal.js";
import { Pagination } from "../components/Pagination.js";
import { UserCard } from "../components/UserCard.js";
import { UserForm } from "../components/UserForm.js";
import { roleService } from "../services/roleService.js";
import { userService } from "../services/userService.js";
import { debounce } from "../utils/debounce.js";
import { normalizeDigits } from "../utils/phoneNumber.js";

const SEARCH_DELAY_MS = 350;
const DEFAULT_PAGE_SIZE = 20;

const createElement = (tagName, className, textContent = "") => {
  const element = document.createElement(tagName);

  element.className = className;
  element.textContent = textContent;

  return element;
};

const createPageHeading = () => {
  const heading = createElement("header", "page-heading");
  const eyebrow = createElement("p", "page-heading__eyebrow", "مدیریت دسترسی");
  const title = createElement("h1", "page-heading__title", "کاربران");
  const description = createElement(
    "p",
    "page-heading__description",
    "فهرست کاربران سامانه و وضعیت فعلی حساب آن‌ها را مشاهده کنید.",
  );

  heading.append(eyebrow, title, description);

  return heading;
};

export const UsersPage = () => {
  const page = createElement("div", "page");
  const toolbar = createElement("div", "page-toolbar");
  const searchLabel = createElement(
    "label",
    "search-box__label",
    "جست‌وجوی کاربران",
  );
  const searchInput = document.createElement("input");
  const createButton = createElement(
    "button",
    "button button--primary",
    "ایجاد کاربر",
  );
  const resultsRegion = createElement("section", "users-region");
  let currentPage = 1;

  searchLabel.htmlFor = "user-search";
  searchInput.id = "user-search";
  searchInput.className = "search-box__input";
  searchInput.type = "search";
  searchInput.placeholder = "نام، شماره موبایل یا نقش";
  searchInput.autocomplete = "off";
  createButton.type = "button";
  resultsRegion.setAttribute("aria-live", "polite");
  resultsRegion.setAttribute("aria-busy", "true");
  toolbar.append(searchLabel, searchInput, createButton);

  const renderLoading = () => {
    resultsRegion.setAttribute("aria-busy", "true");
    resultsRegion.replaceChildren(
      createElement("p", "loading-state", "در حال دریافت کاربران..."),
    );
  };

  const renderError = (retry) => {
    const errorState = createElement("div", "error-state");
    const message = createElement(
      "p",
      "error-state__message",
      "دریافت فهرست کاربران انجام نشد.",
    );
    const retryButton = createElement(
      "button",
      "button button--primary",
      "تلاش مجدد",
    );

    retryButton.type = "button";
    retryButton.addEventListener("click", retry);
    errorState.append(message, retryButton);
    resultsRegion.replaceChildren(errorState);
  };

  const openUserForm = async (user, triggerElement) => {
    triggerElement.disabled = true;

    try {
      const roleResponse = await roleService.getRoles();
      let modal;
      const form = UserForm({
        user,
        roles: roleResponse,
        onSubmit: async (values) => {
          if (user) await userService.updateUser(user.id, values);
          else await userService.createUser(values);

          modal.close();
          currentPage = 1;
          await loadUsers();
        },
        onCancel: () => modal.close(),
      });

      modal = Modal({
        title: user ? "ویرایش کاربر" : "ایجاد کاربر جدید",
        content: form,
        triggerElement,
      });
    } catch {
      renderError(loadUsers, "دریافت اطلاعات فرم انجام نشد.");
    } finally {
      triggerElement.disabled = false;
    }
  };

  const renderUsers = ({ items, page: activePage, totalItems, totalPages }) => {
    if (!items.length) {
      resultsRegion.replaceChildren(
        EmptyState({
          title: "کاربری پیدا نشد",
          description: "عبارت جست‌وجو را تغییر دهید و دوباره تلاش کنید.",
        }),
      );
      return;
    }

    const list = createElement("ul", "user-list");
    const resultCount = createElement(
      "p",
      "results-count",
      `${totalItems} کاربر`,
    );

    items.forEach((user) =>
      list.append(
        UserCard({
          user,
          onEdit: (selectedUser, triggerElement) =>
            openUserForm(selectedUser, triggerElement),
        }),
      ),
    );
    resultsRegion.replaceChildren(resultCount, list);

    if (totalPages > 1) {
      resultsRegion.append(
        Pagination({
          activePage,
          totalPages,
          onPageChange: (selectedPage) => {
            currentPage = selectedPage;
            loadUsers();
          },
        }),
      );
    }
  };

  const loadUsers = async () => {
    renderLoading();

    try {
      const response = await userService.getUsers({
        search: normalizeDigits(searchInput.value),
        page: currentPage,
        pageSize: DEFAULT_PAGE_SIZE,
      });
      renderUsers(response.data);
    } catch {
      renderError(loadUsers);
    } finally {
      resultsRegion.setAttribute("aria-busy", "false");
    }
  };

  searchInput.addEventListener(
    "input",
    debounce(() => {
      currentPage = 1;
      loadUsers();
    }, SEARCH_DELAY_MS),
  );
  createButton.addEventListener("click", () =>
    openUserForm(null, createButton),
  );

  page.append(createPageHeading(), toolbar, resultsRegion);
  loadUsers();

  return page;
};
