import { roleService } from "../services/roleService.js";

const node = (tag, className, text = "") => {
  const element = document.createElement(tag);
  element.className = className;
  element.textContent = text;
  return element;
};

const createRoleForm = ({ onCreated }) => {
  const form = node("form", "role-create");
  const nameLabel = node("label", "form-field");
  const nameText = node("span", "form-field__label", "نام فنی نقش");
  const nameInput = document.createElement("input");
  const nameError = node("span", "form-field__error");
  const displayLabel = node("label", "form-field");
  const displayText = node("span", "form-field__label", "عنوان نمایشی");
  const displayInput = document.createElement("input");
  const displayError = node("span", "form-field__error");
  const submit = node("button", "button button--primary", "ایجاد نقش");

  nameInput.className = "form-field__input";
  nameInput.placeholder = "مثال: project_reviewer";
  nameInput.dir = "ltr";
  displayInput.className = "form-field__input";
  displayInput.placeholder = "مثال: بازبین پروژه";
  submit.type = "submit";
  nameLabel.append(nameText, nameInput, nameError);
  displayLabel.append(displayText, displayInput, displayError);
  form.append(nameLabel, displayLabel, submit);

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const name = nameInput.value.trim();
    const displayName = displayInput.value.trim();
    const validName = /^[a-z][a-z0-9_]{2,79}$/.test(name);
    const validDisplayName = displayName.length >= 2 && displayName.length <= 120;
    nameError.textContent = validName
      ? ""
      : "حداقل سه کاراکتر؛ فقط حروف کوچک انگلیسی، عدد و زیرخط.";
    displayError.textContent = validDisplayName
      ? ""
      : "عنوان باید بین ۲ تا ۱۲۰ کاراکتر باشد.";
    nameInput.setAttribute("aria-invalid", String(!validName));
    displayInput.setAttribute("aria-invalid", String(!validDisplayName));
    if (!validName || !validDisplayName) return;

    submit.disabled = true;
    submit.textContent = "در حال ایجاد...";
    try {
      const role = await roleService.createRole({ name, displayName });
      form.reset();
      await onCreated(role);
    } catch (error) {
      nameError.textContent = error.message;
      nameInput.setAttribute("aria-invalid", "true");
    } finally {
      submit.disabled = false;
      submit.textContent = "ایجاد نقش";
    }
  });
  return form;
};

const createPermissionMatrix = ({ permissions, selectedCodes, onChange }) => {
  const matrix = node("div", "permission-matrix");
  const groups = permissions.reduce((result, permission) => {
    const items = result.get(permission.groupName) ?? [];
    items.push(permission);
    result.set(permission.groupName, items);
    return result;
  }, new Map());

  groups.forEach((items, groupName) => {
    const section = node("section", "permission-group");
    const header = node("div", "permission-group__header");
    const title = node("h3", "permission-group__title", groupName);
    const toggleLabel = node("label", "permission-group__toggle");
    const toggle = document.createElement("input");
    const toggleText = node("span", "", "انتخاب همه");
    toggle.type = "checkbox";
    toggle.checked = items.every(({ code }) => selectedCodes.has(code));
    toggle.indeterminate =
      !toggle.checked && items.some(({ code }) => selectedCodes.has(code));
    toggle.addEventListener("change", () => {
      items.forEach(({ code }) =>
        toggle.checked ? selectedCodes.add(code) : selectedCodes.delete(code),
      );
      onChange();
    });
    toggleLabel.append(toggle, toggleText);
    header.append(title, toggleLabel);
    section.append(header);

    items.forEach((permission) => {
      const label = node("label", "permission-item");
      const checkbox = document.createElement("input");
      const detail = node("span", "permission-item__detail");
      const code = node("code", "permission-item__code", permission.code);
      const description = node(
        "span",
        "permission-item__description",
        permission.description,
      );
      checkbox.type = "checkbox";
      checkbox.value = permission.code;
      checkbox.checked = selectedCodes.has(permission.code);
      checkbox.addEventListener("change", () => {
        checkbox.checked
          ? selectedCodes.add(permission.code)
          : selectedCodes.delete(permission.code);
        onChange();
      });
      detail.append(code, description);
      if (permission.isSensitive) {
        detail.append(node("span", "permission-item__sensitive", "حساس"));
      }
      label.append(checkbox, detail);
      section.append(label);
    });
    matrix.append(section);
  });
  return matrix;
};

export const RolesPage = () => {
  const page = node("div", "page roles-page");
  const heading = node("header", "page-heading");
  const eyebrow = node("p", "page-heading__eyebrow", "کنترل دسترسی");
  const title = node("h1", "page-heading__title", "نقش‌ها و دسترسی‌ها");
  const description = node(
    "p",
    "page-heading__description",
    "نقش‌ها را از بک‌اند دریافت کنید و دسترسی‌های هر نقش را مدیریت کنید.",
  );
  const content = node("div", "roles-content");
  heading.append(eyebrow, title, description);
  page.append(heading, content);

  let roles = [];
  let permissions = [];
  let activeRoleId = null;

  const renderError = (message, retry) => {
    const state = node("div", "error-state");
    const retryButton = node("button", "button button--primary", "تلاش مجدد");
    retryButton.type = "button";
    retryButton.addEventListener("click", retry);
    state.append(node("p", "error-state__message", message), retryButton);
    content.replaceChildren(state);
  };

  const render = () => {
    const sidebar = node("aside", "role-panel");
    const listTitle = node("h2", "role-panel__title", "نقش‌ها");
    const list = node("div", "role-list");
    const workspace = node("section", "role-workspace");
    const activeRole = roles.find(({ id }) => id === activeRoleId) ?? roles[0];

    roles.forEach((role) => {
      const button = node("button", "role-list__item");
      button.type = "button";
      button.classList.toggle("role-list__item--active", role.id === activeRole?.id);
      button.append(
        node("strong", "", role.displayName),
        node("span", "", role.name),
      );
      button.addEventListener("click", () => {
        activeRoleId = role.id;
        render();
      });
      list.append(button);
    });
    sidebar.append(listTitle, list, createRoleForm({
      onCreated: async (role) => {
        roles.push(role);
        activeRoleId = role.id;
        render();
      },
    }));

    if (!activeRole) {
      workspace.append(node("p", "loading-state", "نقشی برای نمایش وجود ندارد."));
      content.replaceChildren(sidebar, workspace);
      return;
    }

    const workspaceHeader = node("header", "role-workspace__header");
    const roleTitle = node("h2", "", activeRole.displayName);
    const roleMeta = node(
      "p",
      "role-workspace__meta",
      `${activeRole.name}${activeRole.isSystem ? " · نقش سیستمی" : ""}`,
    );
    const feedback = node("p", "form-feedback");
    const actions = node("div", "role-workspace__actions");
    const save = node("button", "button button--primary", "ذخیره دسترسی‌ها");
    const initialCodes = new Set(activeRole.permissions.map(({ code }) => code));
    const selectedCodes = new Set(initialCodes);

    const refreshMatrix = () => {
      const matrix = createPermissionMatrix({
        permissions,
        selectedCodes,
        onChange: refreshMatrix,
      });
      const changed =
        selectedCodes.size !== initialCodes.size ||
        [...selectedCodes].some((code) => !initialCodes.has(code));
      save.disabled = !changed;
      workspace.querySelector(".permission-matrix")?.replaceWith(matrix);
    };

    save.type = "button";
    save.disabled = true;
    save.addEventListener("click", async () => {
      const changedSensitive = permissions.some(
        ({ code, isSensitive }) =>
          isSensitive && selectedCodes.has(code) !== initialCodes.has(code),
      );
      const confirmed =
        !changedSensitive ||
        window.confirm("دسترسی حساس تغییر کرده است. این تغییر را تأیید می‌کنید؟");
      if (!confirmed) return;

      save.disabled = true;
      save.textContent = "در حال ذخیره...";
      try {
        const updated = await roleService.updatePermissions(activeRole.id, {
          permissionCodes: [...selectedCodes],
          confirmed: changedSensitive,
        });
        roles = roles.map((role) => (role.id === updated.id ? updated : role));
        render();
      } catch (error) {
        feedback.textContent = error.message;
        feedback.dataset.type = "error";
        save.disabled = false;
        save.textContent = "ذخیره دسترسی‌ها";
      }
    });
    workspaceHeader.append(roleTitle, roleMeta);
    actions.append(save);
    workspace.append(
      workspaceHeader,
      feedback,
      createPermissionMatrix({
        permissions,
        selectedCodes,
        onChange: refreshMatrix,
      }),
      actions,
    );
    content.replaceChildren(sidebar, workspace);
  };

  const load = async () => {
    content.replaceChildren(node("p", "loading-state", "در حال دریافت نقش‌ها..."));
    try {
      [roles, permissions] = await Promise.all([
        roleService.getRoles(),
        roleService.getPermissions(),
      ]);
      activeRoleId = roles[0]?.id ?? null;
      render();
    } catch (error) {
      renderError(error.message ?? "دریافت نقش‌ها انجام نشد.", load);
    }
  };

  load();
  return page;
};
