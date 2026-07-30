const element = (tag, className, text = "") => {
  const node = document.createElement(tag);
  node.className = className;
  node.textContent = text;
  return node;
};

export const UserCard = ({ user, canManage, onEdit, onToggleStatus }) => {
  const item = element("li", "user-card");
  const identity = element("div", "user-card__identity");
  const name = element("h2", "user-card__name", user.displayName);
  const mobile = element("span", "user-card__phone", user.mobile);
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

  identity.append(name, mobile);
  item.append(identity, roles, status);
  if (canManage) {
    const actions = element("div", "user-card__actions");
    const edit = element("button", "button button--ghost", "مدیریت");
    const toggleStatus = element(
      "button",
      user.isActive ? "button button--danger" : "button button--ghost",
      user.isActive ? "غیرفعال‌سازی" : "فعال‌سازی مجدد",
    );
    edit.type = "button";
    toggleStatus.type = "button";
    edit.addEventListener("click", () => onEdit(user, edit));
    toggleStatus.addEventListener("click", () =>
      onToggleStatus(user, toggleStatus),
    );
    actions.append(edit, toggleStatus);
    item.append(actions);
  }
  return item;
};
