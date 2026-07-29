const element = (tag, className, text = "") => {
  const node = document.createElement(tag);
  node.className = className;
  node.textContent = text;
  return node;
};

export const UserCard = ({ user, canManage, onEdit }) => {
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
    const edit = element("button", "button button--ghost", "مدیریت");
    edit.type = "button";
    edit.addEventListener("click", () => onEdit(user, edit));
    item.append(edit);
  }
  return item;
};
