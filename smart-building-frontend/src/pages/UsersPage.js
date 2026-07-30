import { sessionStore } from "../app/sessionStore.js";
import { EmptyState } from "../components/EmptyState.js";
import { Modal } from "../components/Modal.js";
import { Pagination } from "../components/Pagination.js";
import { UserCard } from "../components/UserCard.js";
import { UserForm } from "../components/UserForm.js";
import { roleService } from "../services/roleService.js";
import { userService } from "../services/userService.js";
import { debounce } from "../utils/debounce.js";
import { normalizeDigits } from "../utils/phoneNumber.js";

const PAGE_SIZE = 20;
const element = (tag, className, text = "") => {
  const node = document.createElement(tag);
  node.className = className;
  node.textContent = text;
  return node;
};

const heading = () => {
  const header = element("header", "page-heading");
  header.append(
    element("p", "page-heading__eyebrow", "مدیریت دسترسی"),
    element("h1", "page-heading__title", "کاربران"),
    element(
      "p",
      "page-heading__description",
      "کاربران واقعی سامانه، نقش‌ها و وضعیت حساب آن‌ها را مدیریت کنید.",
    ),
  );
  return header;
};

const includesQuery = (user, query) => {
  const normalized = normalizeDigits(query).trim().toLocaleLowerCase("fa-IR");
  if (!normalized) return true;
  return [
    user.displayName,
    user.mobile,
    ...user.roles.flatMap(({ name, displayName }) => [name, displayName]),
  ].some((value) => value.toLocaleLowerCase("fa-IR").includes(normalized));
};

export const UsersPage = () => {
  const page = element("div", "page");
  const toolbar = element("div", "page-toolbar");
  const searchLabel = element("label", "search-box__label", "جست‌وجوی کاربران");
  const search = document.createElement("input");
  const create = element("button", "button button--primary", "ایجاد کاربر");
  const region = element("section", "users-region");
  const canManage = sessionStore
    .getCurrentUser()
    ?.permissions.includes("users.manage");
  let users = [];
  let currentPage = 1;

  searchLabel.htmlFor = "user-search";
  search.id = "user-search";
  search.className = "search-box__input";
  search.type = "search";
  search.placeholder = "نام، شماره موبایل یا نقش";
  search.autocomplete = "off";
  create.type = "button";
  create.hidden = !canManage;
  region.setAttribute("aria-live", "polite");
  toolbar.append(searchLabel, search, create);

  const renderError = (message, retry) => {
    const state = element("div", "error-state");
    const button = element("button", "button button--primary", "تلاش مجدد");
    button.type = "button";
    button.addEventListener("click", retry);
    state.append(element("p", "error-state__message", message), button);
    region.replaceChildren(state);
  };

  const render = () => {
    const filtered = users.filter((user) => includesQuery(user, search.value));
    const totalPages = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE));
    currentPage = Math.min(currentPage, totalPages);
    const start = (currentPage - 1) * PAGE_SIZE;
    const visibleUsers = filtered.slice(start, start + PAGE_SIZE);

    if (!visibleUsers.length) {
      region.replaceChildren(
        EmptyState({
          title: "کاربری پیدا نشد",
          description: "عبارت جست‌وجو را تغییر دهید و دوباره تلاش کنید.",
        }),
      );
      return;
    }

    const list = element("ul", "user-list");
    visibleUsers.forEach((user) =>
      list.append(
        UserCard({
          user,
          canManage,
          onEdit: openForm,
          onToggleStatus: async (targetUser, trigger) => {
            const action = targetUser.isActive ? "غیرفعال" : "فعال";
            if (
              !window.confirm(
                `کاربر «${targetUser.displayName}» ${action} شود؟`,
              )
            ) {
              return;
            }
            trigger.disabled = true;
            try {
              await userService.updateStatus(targetUser.id, {
                isActive: !targetUser.isActive,
                reason: `${action}‌سازی از فهرست مدیریت کاربران`,
              });
              await loadUsers();
            } catch (error) {
              window.alert(error.message);
              trigger.disabled = false;
            }
          },
        }),
      ),
    );
    region.replaceChildren(
      element("p", "results-count", `${filtered.length} کاربر`),
      list,
    );
    if (totalPages > 1) {
      region.append(
        Pagination({
          activePage: currentPage,
          totalPages,
          onPageChange: (pageNumber) => {
            currentPage = pageNumber;
            render();
          },
        }),
      );
    }
  };

  const loadUsers = async () => {
    region.replaceChildren(
      element("p", "loading-state", "در حال دریافت کاربران..."),
    );
    region.setAttribute("aria-busy", "true");
    try {
      users = await userService.getUsers();
      render();
    } catch (error) {
      renderError(error.message ?? "دریافت کاربران انجام نشد.", loadUsers);
    } finally {
      region.setAttribute("aria-busy", "false");
    }
  };

  const openForm = async (user = null, trigger = create) => {
    trigger.disabled = true;
    try {
      const roles = await roleService.getRoles();
      let modal;
      const form = UserForm({
        user,
        roles,
        onSubmit: async (values) => {
          if (!user) {
            await userService.createUser(values);
          } else {
            const initialRoleIds = user.roles.map(({ id }) => id).sort();
            const nextRoleIds = [...values.roleIds].sort();
            const rolesChanged =
              initialRoleIds.join(",") !== nextRoleIds.join(",");
            if (
              (rolesChanged || values.statusChanged) &&
              !window.confirm("تغییر نقش یا وضعیت این کاربر را تأیید می‌کنید؟")
            ) {
              throw new Error("تغییرات توسط شما لغو شد.");
            }
            if (rolesChanged) {
              await userService.updateRoles(user.id, values.roleIds);
            }
            if (values.statusChanged) {
              await userService.updateStatus(user.id, values);
            }
          }
          modal.close();
          currentPage = 1;
          await loadUsers();
        },
        onCancel: () => modal.close(),
      });
      modal = Modal({
        title: user ? "مدیریت کاربر" : "ایجاد کاربر جدید",
        content: form,
        triggerElement: trigger,
      });
    } catch (error) {
      renderError(error.message ?? "دریافت اطلاعات فرم انجام نشد.", loadUsers);
    } finally {
      trigger.disabled = false;
    }
  };

  search.addEventListener(
    "input",
    debounce(() => {
      currentPage = 1;
      render();
    }, 300),
  );
  create.addEventListener("click", () => openForm());
  page.append(heading(), toolbar, region);
  loadUsers();
  return page;
};
