const element = (tag, className, text = "") => {
  const node = document.createElement(tag);
  node.className = className;
  node.textContent = text;
  return node;
};

export const UserCard = ({
  user,
  canManage,
  canEditOwnName,
  onEdit,
  onEditOwnName,
  onToggleStatus,
}) => {
  const item = element("li", "user-card");
  const identity = element("div", "user-card__identity");
  const name = element("h2", "user-card__name", user.displayName);
  const identifier = element("span", "user-card__identifier", `شناسه کاربر: ${user.id}`);
  const mobile = element("span", "user-card__phone", `شماره ثبت‌شده: ${user.mobile}`);
  mobile.title = "شماره برای حفظ حریم خصوصی به‌صورت ماسک‌شده نمایش داده می‌شود.";
  const roleNames = user.roles.map(({ displayName }) => displayName).join("، ");
  const roles = element(
    "span",
    "user-card__role",
    roleNames || "بدون نقش",
  );
  const status = element(
    "span",
    `status-badge status-badge--${user.isActive ? "active" : "inactive"}`,
    user.isActive ? "فعال" : "غیرفعال",
  );

  identity.append(name, identifier, mobile);
  item.append(identity, roles, status);
  if (canManage || canEditOwnName) {
    const actions = element("div", "user-card__actions");
    if (canEditOwnName && !canManage) {
      const editName = element("button", "button button--ghost", "تغییر نام من");
      editName.type = "button";
      editName.addEventListener("click", () => onEditOwnName(user, editName));
      actions.append(editName);
    }
    if (canManage) {
      const edit = element("button", "button button--ghost", "ویرایش نام، نقش و دسترسی");
      const toggleStatus = element("button", user.isActive ? "button button--danger" : "button button--ghost", user.isActive ? "غیرفعال‌سازی" : "فعال‌سازی مجدد");
      edit.type = "button"; toggleStatus.type = "button";
      edit.addEventListener("click", () => onEdit(user, edit));
      toggleStatus.addEventListener("click", () => onToggleStatus(user, toggleStatus));
      actions.append(edit, toggleStatus);
    }
    item.append(actions);
  }
  return item;
};
