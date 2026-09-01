import { clearNavigationGuard, createUnsavedChangesGuard, setNavigationGuard } from "../app/navigationGuard.js";
import { sessionStore } from "../app/sessionStore.js";
import { confirmDialog } from "../components/AppDialog.js";
import { roleService } from "../services/roleService.js";

const GROUP_LABELS = Object.freeze({
  Users: "کاربران", Roles: "نقش‌ها و دسترسی‌ها", Pilots: "پرونده‌های پایلوت",
  Projects: "پروژه و طبقات", Stages: "مراحل ۱۹گانه", "Stage 1": "مرحله اول",
  Gates: "گیت‌های تأیید", "Gate Approval": "تأیید مرحله و گیت", Forms: "فرم‌های رسمی",
  DWG: "نقشه‌های DWG", Missions: "مأموریت‌ها", Checklists: "چک‌لیست‌ها",
  Incidents: "رخدادها", "Customer Success": "پشتیبانی", Commercial: "فروش و امور تجاری",
  Reports: "گزارش‌ها", Notifications: "اعلان‌ها", Audit: "تاریخچه تغییرات",
  System: "تنظیمات سامانه", Preferences: "تنظیمات شخصی", "External Platform": "پلتفرم اصلی",
});
const ACTION_LABELS = Object.freeze({
  read: "مشاهده", read_all: "مشاهده همه", create: "ایجاد", update: "ویرایش",
  manage: "مدیریت کامل", delete: "حذف", approve: "تأیید", reject: "رد",
  submit: "ارسال", assign: "تخصیص", close: "بستن", reopen: "بازگشایی",
  export: "دریافت خروجی", print: "چاپ", upload: "بارگذاری", download: "دریافت فایل",
  clone: "ساخت نسخه مشابه", start: "شروع", review: "بازبینی", escalate: "ارجاع فوری",
});
const SCOPE_LABELS = Object.freeze({ ALL: "همه اطلاعات", ASSIGNED: "فقط موارد تخصیص‌یافته", CREATED_BY_ME: "ایجادشده توسط کاربر", ROLE_RELATED: "مرتبط با مسئولیت نقش", PILOT_MEMBER: "پایلوت‌های تحت مسئولیت", READ_ONLY: "فقط مشاهده" });
const MENU_LABELS = Object.freeze({ pilots: "پایلوت‌ها", projects: "پروژه‌ها", stages: "مراحل", gates: "گیت‌ها", forms: "فرم‌ها", reports: "گزارش‌ها", incidents: "رخدادها", users: "کاربران", roles: "نقش‌ها", access: "دسترسی‌ها", missions: "مأموریت‌ها", checklists: "چک‌لیست‌ها", commercial: "فروش", notifications: "اعلان‌ها", training: "آموزش", feedback: "بازخورد", "customer-success": "پشتیبانی", "external-platform": "پلتفرم اصلی", "*": "تمام بخش‌های سامانه" });

const node = (tag, className = "", text = "") => { const element = document.createElement(tag); element.className = className; element.textContent = text; return element; };
const permissionTitle = (permission) => {
  const action = permission.code.split(".").at(-1);
  return ACTION_LABELS[action] ?? permission.description;
};
const validateRoleName = (value) => /^[a-z][a-z0-9_]{2,79}$/.test(value);

const createRoleComposer = ({ title, submitLabel, initialDisplayName = "", onSubmit, onCancel }) => {
  const form = node("form", "role-composer");
  form.append(node("h3", "role-composer__title", title));
  const displayLabel = node("label", "form-field");
  const display = document.createElement("input"); display.className = "form-field__input"; display.value = initialDisplayName; display.placeholder = "مثال: بازبین فنی";
  displayLabel.append(node("span", "form-field__label", "نام فارسی نقش"), display);
  const nameLabel = node("label", "form-field");
  const name = document.createElement("input"); name.className = "form-field__input"; name.dir = "ltr"; name.placeholder = "technical_reviewer";
  nameLabel.append(node("span", "form-field__label", "کد فنی نقش"), name);
  const error = node("p", "form-field__error");
  const actions = node("div", "role-composer__actions");
  const submit = node("button", "button button--primary", submitLabel); submit.type = "submit";
  actions.append(submit);
  if (onCancel) { const cancel = node("button", "button button--ghost", "لغو"); cancel.type = "button"; cancel.addEventListener("click", onCancel); actions.append(cancel); }
  form.append(displayLabel, nameLabel, error, actions);
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const values = { displayName: display.value.trim(), name: name.value.trim() };
    if (values.displayName.length < 2 || !validateRoleName(values.name)) { error.textContent = "نام فارسی حداقل دو حرف و کد فنی حداقل سه حرف انگلیسی کوچک داشته باشد."; return; }
    submit.disabled = true;
    try { await onSubmit(values); }
    catch (exception) { error.textContent = exception.message ?? "ثبت نقش انجام نشد."; submit.disabled = false; }
  });
  return form;
};

const createPermissionMatrix = ({ permissions, selectedCodes, searchTerm, disabled, onChange }) => {
  const matrix = node("div", "permission-matrix");
  const normalizedSearch = searchTerm.trim().toLocaleLowerCase("fa");
  const visible = permissions.filter((permission) => !normalizedSearch || `${permission.code} ${permission.description} ${GROUP_LABELS[permission.groupName] ?? permission.groupName}`.toLocaleLowerCase("fa").includes(normalizedSearch));
  const groups = visible.reduce((result, permission) => { const items = result.get(permission.groupName) ?? []; items.push(permission); result.set(permission.groupName, items); return result; }, new Map());
  if (!groups.size) { matrix.append(node("p", "role-empty", "دسترسی مطابق جست‌وجوی شما پیدا نشد.")); return matrix; }
  groups.forEach((items, groupName) => {
    const section = node("section", "permission-group");
    const header = node("header", "permission-group__header");
    const heading = node("div", "permission-group__heading");
    const selectedCount = items.filter(({ code }) => selectedCodes.has(code)).length;
    const groupTitle = node("h3", "permission-group__title", GROUP_LABELS[groupName] ?? groupName);
    groupTitle.id = `permission-group-${String(groupName).replace(/[^a-z0-9]+/gi, "-").toLowerCase()}`;
    heading.append(groupTitle, node("span", "permission-group__count", `${selectedCount} از ${items.length} دسترسی فعال`));
    const groupActions = node("div", "permission-group__actions");
    const selectAll = node("button", "button-link", "انتخاب همه"); const clear = node("button", "button-link", "پاک‌کردن گروه");
    selectAll.type = clear.type = "button"; selectAll.disabled = clear.disabled = disabled;
    selectAll.addEventListener("click", () => { items.forEach(({ code }) => selectedCodes.add(code)); onChange(); });
    clear.addEventListener("click", () => { items.forEach(({ code }) => selectedCodes.delete(code)); onChange(); });
    groupActions.append(selectAll, clear); header.append(heading, groupActions); section.append(header);
    const tableWrap = node("div", "permission-table-wrap");
    const table = node("table", "permission-table");
    table.setAttribute("aria-labelledby", groupTitle.id);
    const tableHead = document.createElement("thead");
    const headerRow = document.createElement("tr");
    ["انتخاب", "مجوز", "توضیح", "وضعیت"].forEach((text) => {
      const cell = document.createElement("th"); cell.scope = "col"; cell.textContent = text; headerRow.append(cell);
    });
    tableHead.append(headerRow);
    const tableBody = document.createElement("tbody");
    items.forEach((permission) => {
      const row = node("tr", `permission-row${permission.isSensitive ? " permission-row--sensitive" : ""}`);
      const checkbox = document.createElement("input"); checkbox.type = "checkbox"; checkbox.checked = selectedCodes.has(permission.code); checkbox.disabled = disabled;
      checkbox.setAttribute("aria-label", `فعال‌کردن مجوز ${permissionTitle(permission)}`);
      checkbox.addEventListener("change", () => { checkbox.checked ? selectedCodes.add(permission.code) : selectedCodes.delete(permission.code); onChange(); });
      const selectCell = document.createElement("td"); selectCell.dataset.label = "انتخاب"; selectCell.append(checkbox);
      const titleCell = document.createElement("td"); titleCell.dataset.label = "مجوز";
      titleCell.append(node("strong", "permission-item__title", permissionTitle(permission)), node("code", "permission-item__code", permission.code));
      const descriptionCell = document.createElement("td"); descriptionCell.dataset.label = "توضیح"; descriptionCell.textContent = permission.description;
      const statusCell = document.createElement("td"); statusCell.dataset.label = "وضعیت";
      statusCell.append(node("span", permission.isSensitive ? "permission-item__sensitive" : "permission-item__regular", permission.isSensitive ? "حساس" : "عادی"));
      row.append(selectCell, titleCell, descriptionCell, statusCell); tableBody.append(row);
    });
    table.append(tableHead, tableBody); tableWrap.append(table); section.append(tableWrap); matrix.append(section);
  });
  return matrix;
};

const createPreview = (preview) => {
  const container = node("section", "access-preview");
  const card = (title, values, formatter = (value) => value) => {
    const section = node("article", "access-preview__card"); section.append(node("h3", "", title));
    const list = node("div", "access-preview__chips");
    if (!values?.length) list.append(node("span", "muted-text", "موردی در این بخش تعریف نشده است."));
    else values.forEach((value) => list.append(node("span", "access-chip", formatter(value))));
    section.append(list); return section;
  };
  container.append(
    card("محدوده اطلاعات", preview.scopes, (value) => SCOPE_LABELS[value] ?? value),
    card("منوهای قابل مشاهده", preview.menu_access, (value) => MENU_LABELS[value] ?? value),
    card("گیت‌های قابل تأیید", preview.gate_access?.approve ?? [], (value) => `گیت ${value}`),
    card("مرحله‌های قابل ویرایش", preview.stage_access?.edit ?? [], (value) => `مرحله ${value}`),
    card("مرحله‌های قابل ارسال", preview.stage_access?.submit ?? [], (value) => `مرحله ${value}`),
    card("مرحله‌های قابل تأیید", preview.stage_access?.approve ?? [], (value) => `مرحله ${value}`),
  );
  return container;
};

export const RolesPage = () => {
  const userPermissions = sessionStore.getCurrentUser()?.permissions ?? [];
  const canRead = userPermissions.includes("roles.read");
  const canManage = userPermissions.includes("roles.manage");
  const page = node("div", "page roles-page");
  const heading = node("header", "page-heading");
  heading.append(node("p", "page-heading__eyebrow", "نقش‌ها و مسئولیت‌ها"), node("h1", "page-heading__title", "تعیین سطح دسترسی کاربران"), node("p", "page-heading__description", "برای هر نقش مشخص کنید کاربر چه بخش‌هایی را می‌بیند و چه عملیاتی می‌تواند انجام دهد. دسترسی‌های حساس با هشدار جداگانه مشخص شده‌اند."));
  const content = node("div", "roles-content"); page.append(heading, content);
  if (!canRead) { content.append(node("p", "error-state__message", "برای مشاهده نقش‌ها و دسترسی‌ها مجوز لازم را ندارید.")); return page; }
  let roles = []; let permissions = []; let activeRoleId = null; let dirty = false;
  const setDirty = (value) => { dirty = value; value ? setNavigationGuard(createUnsavedChangesGuard("تغییرات دسترسی این نقش هنوز ذخیره نشده است.")) : clearNavigationGuard(); };

  const render = () => {
    const activeRole = roles.find(({ id }) => id === activeRoleId) ?? roles[0];
    const selectorPanel = node("section", "role-panel");
    const selectorLabel = node("label", "role-selector-field");
    selectorLabel.append(node("span", "form-field__label", "نقش سامانه"));
    const selector = document.createElement("select"); selector.className = "form-field__input role-select";
    roles.forEach((role) => selector.append(new Option(`${role.displayName} — ${role.isActive ? "فعال" : "غیرفعال"} — ${role.permissions.length} مجوز`, role.id)));
    selector.value = activeRole?.id ?? "";
    selector.setAttribute("aria-label", "انتخاب نقش سامانه");
    selector.addEventListener("change", async () => {
      const previousId = activeRoleId;
      if (dirty && !(await confirmDialog({ title: "تغییرات ذخیره‌نشده", message: "تغییرات این نقش ذخیره نشده است. نقش دیگری باز شود؟", confirmLabel: "تغییر نقش", triggerElement: selector }))) {
        selector.value = previousId ?? ""; return;
      }
      setDirty(false); activeRoleId = Number(selector.value); render();
    });
    selectorLabel.append(selector);
    const selectorMeta = node("div", "role-selector-meta");
    if (activeRole) selectorMeta.append(
      node("code", "role-workspace__code", activeRole.name),
      node("span", `role-status${activeRole.isActive ? " is-active" : ""}`, activeRole.isActive ? "فعال" : "غیرفعال"),
      node("span", "role-panel__count", `${roles.length} نقش در سامانه`),
    );
    selectorPanel.append(selectorLabel, selectorMeta);
    if (canManage) {
      const addToggle = node("button", "button button--ghost role-panel__add", "ایجاد نقش جدید"); addToggle.type = "button";
      addToggle.addEventListener("click", () => { addToggle.replaceWith(createRoleComposer({ title: "نقش جدید", submitLabel: "ایجاد نقش", onCancel: render, onSubmit: async (values) => { const role = await roleService.createRole(values); roles.push(role); activeRoleId = role.id; render(); } })); });
      selectorPanel.append(addToggle);
    }
    const workspace = node("section", "role-workspace");
    if (!activeRole) { workspace.append(node("p", "loading-state", "نقشی برای نمایش وجود ندارد.")); content.replaceChildren(selectorPanel, workspace); return; }
    const initialCodes = new Set(activeRole.permissions.map(({ code }) => code));
    const selectedCodes = new Set(initialCodes);
    let searchTerm = "";
    const workspaceHeader = node("header", "role-workspace__header");
    const titleBlock = node("div", "role-workspace__identity"); titleBlock.append(node("h2", "", activeRole.displayName), node("code", "role-workspace__code", activeRole.name));
    const stats = node("div", "role-stats"); stats.append(node("span", "role-stat", `${activeRole.permissions.length} دسترسی فعال`), node("span", "role-stat", activeRole.isSystem ? "نقش سیستمی" : "نقش سفارشی"), node("span", `role-stat${activeRole.isActive ? " is-success" : " is-muted"}`, activeRole.isActive ? "فعال" : "غیرفعال"));
    workspaceHeader.append(titleBlock, stats);
    const notice = node("p", "role-readonly-notice", canManage ? "تغییر دسترسی‌ها پس از ذخیره در backend اعمال و در ورود بعدی یا refresh دسترسی کاربر به‌روز می‌شود." : "شما فقط امکان مشاهده مسئولیت‌های این نقش را دارید.");
    const tools = node("div", "role-tools");
    const search = document.createElement("input"); search.type = "search"; search.className = "form-field__input role-search"; search.placeholder = "جست‌وجوی دسترسی، مثال: مشاهده پایلوت"; search.setAttribute("aria-label", "جست‌وجوی دسترسی‌ها");
    const previewButton = node("button", "button button--ghost", "پیش‌نمایش مسئولیت‌ها"); previewButton.type = "button";
    tools.append(search, previewButton);
    const matrixHost = node("div", "permission-matrix-host");
    const previewHost = node("div", "access-preview-host");
    const feedback = node("p", "form-feedback");
    const actions = node("div", "role-workspace__actions");
    const save = node("button", "button button--primary", "ذخیره تغییرات"); const reset = node("button", "button button--ghost", "بازنشانی"); const edit = node("button", "button button--ghost", "ویرایش عنوان نقش"); const clone = node("button", "button button--ghost", "ساخت نقش مشابه"); const toggleStatus = node("button", "button button--ghost", activeRole.isActive ? "غیرفعال‌کردن نقش" : "فعال‌کردن نقش"); const remove = node("button", "button button--danger", "حذف نقش");
    [save, reset, edit, clone, toggleStatus, remove].forEach((button) => { button.type = "button"; }); remove.hidden = activeRole.isSystem || !canManage; toggleStatus.hidden = activeRole.isSystem || !canManage; edit.hidden = clone.hidden = !canManage; save.hidden = reset.hidden = !canManage;
    const hasChanges = () => selectedCodes.size !== initialCodes.size || [...selectedCodes].some((code) => !initialCodes.has(code));
    const refreshMatrix = () => { matrixHost.replaceChildren(createPermissionMatrix({ permissions, selectedCodes, searchTerm, disabled: !canManage, onChange: () => { setDirty(hasChanges()); save.disabled = !dirty; reset.disabled = !dirty; refreshMatrix(); } })); save.disabled = reset.disabled = !hasChanges(); };
    search.addEventListener("input", () => { searchTerm = search.value; refreshMatrix(); });
    previewButton.addEventListener("click", async () => { previewButton.disabled = true; previewHost.replaceChildren(node("p", "loading-state", "در حال ساخت پیش‌نمایش…")); try { previewHost.replaceChildren(createPreview(await roleService.getAccessPreview(activeRole.id))); } catch (error) { previewHost.replaceChildren(node("p", "error-state__message", error.message ?? "پیش‌نمایش دریافت نشد.")); } finally { previewButton.disabled = false; } });
    reset.addEventListener("click", () => { selectedCodes.clear(); initialCodes.forEach((code) => selectedCodes.add(code)); setDirty(false); refreshMatrix(); });
    save.addEventListener("click", async () => {
      const sensitiveChanged = permissions.some(({ code, isSensitive }) => isSensitive && selectedCodes.has(code) !== initialCodes.has(code));
      if (sensitiveChanged && !(await confirmDialog({ title: "تغییر دسترسی حساس", message: "این تغییر می‌تواند امکان تأیید، حذف یا مدیریت اطلاعات مهم را تغییر دهد. ادامه می‌دهید؟", confirmLabel: "تأیید و ذخیره", triggerElement: save }))) return;
      save.disabled = true; save.textContent = "در حال ذخیره…";
      try { const updated = await roleService.updatePermissions(activeRole.id, { permissionCodes: [...selectedCodes], confirmed: sensitiveChanged }); roles = roles.map((role) => role.id === updated.id ? updated : role); setDirty(false); feedback.textContent = "دسترسی‌های نقش ذخیره شد."; feedback.dataset.type = "success"; render(); }
      catch (error) { feedback.textContent = error.message ?? "ذخیره دسترسی‌ها انجام نشد."; feedback.dataset.type = "error"; save.disabled = false; save.textContent = "ذخیره تغییرات"; }
    });
    edit.addEventListener("click", () => {
      const form = node("form", "role-composer"); const input = document.createElement("input"); input.className = "form-field__input"; input.value = activeRole.displayName;
      const label = node("label", "form-field"); label.append(node("span", "form-field__label", "عنوان فارسی نقش"), input);
      const error = node("p", "form-field__error"); const submit = node("button", "button button--primary", "ذخیره عنوان"); submit.type = "submit"; const cancel = node("button", "button button--ghost", "لغو"); cancel.type = "button"; cancel.addEventListener("click", render);
      const formActions = node("div", "role-composer__actions"); formActions.append(submit, cancel); form.append(node("h3", "role-composer__title", "ویرایش مشخصات نقش"), label, error, formActions);
      form.addEventListener("submit", async (event) => { event.preventDefault(); const displayName = input.value.trim(); if (displayName.length < 2) { error.textContent = "عنوان نقش حداقل دو حرف باشد."; return; } submit.disabled = true; try { const updated = await roleService.updateRole(activeRole.id, { displayName }); roles = roles.map((role) => role.id === updated.id ? updated : role); render(); } catch (exception) { error.textContent = exception.message; submit.disabled = false; } });
      actions.replaceChildren(form);
    });
    clone.addEventListener("click", () => { actions.replaceChildren(createRoleComposer({ title: `ساخت نقش بر اساس «${activeRole.displayName}»`, submitLabel: "ساخت نسخه مشابه", onCancel: render, onSubmit: async (values) => { const role = await roleService.cloneRole(activeRole.id, values); roles.push(role); activeRoleId = role.id; render(); } })); });
    toggleStatus.addEventListener("click", async () => { if (!(await confirmDialog({ title: activeRole.isActive ? "غیرفعال‌کردن نقش" : "فعال‌کردن نقش", message: activeRole.isActive ? "کاربران دارای این نقش دیگر دسترسی‌های آن را دریافت نمی‌کنند. ادامه می‌دهید؟" : "این نقش دوباره برای کاربران فعال شود؟", confirmLabel: activeRole.isActive ? "غیرفعال کن" : "فعال کن", triggerElement: toggleStatus }))) return; const updated = await roleService.updateRole(activeRole.id, { isActive: !activeRole.isActive }); roles = roles.map((role) => role.id === updated.id ? updated : role); render(); });
    remove.addEventListener("click", async () => { if (!(await confirmDialog({ title: "حذف نقش", message: `نقش «${activeRole.displayName}» حذف شود؟ نقش دارای کاربر قابل حذف نیست.`, confirmLabel: "حذف نقش", confirmClassName: "button button--danger", triggerElement: remove }))) return; try { await roleService.deleteRole(activeRole.id); roles = roles.filter(({ id }) => id !== activeRole.id); activeRoleId = roles[0]?.id ?? null; render(); } catch (error) { feedback.textContent = error.message; feedback.dataset.type = "error"; } });
    actions.append(save, reset, edit, clone, toggleStatus, remove);
    workspace.append(workspaceHeader, notice, tools, feedback, matrixHost, previewHost, actions); refreshMatrix(); content.replaceChildren(selectorPanel, workspace);
  };
  const load = async () => { content.replaceChildren(node("p", "loading-state", "در حال دریافت نقش‌ها و مسئولیت‌ها…")); try { const [fetchedRoles, fetchedPermissions] = await Promise.all([roleService.getRoles(), roleService.getPermissions()]); roles = fetchedRoles.filter(({ isActive }) => isActive); permissions = fetchedPermissions; activeRoleId = roles[0]?.id ?? null; render(); } catch (error) { const retry = node("button", "button button--primary", "تلاش مجدد"); retry.type = "button"; retry.addEventListener("click", load); content.replaceChildren(node("p", "error-state__message", error.message ?? "دریافت نقش‌ها انجام نشد."), retry); } };
  load(); return page;
};
