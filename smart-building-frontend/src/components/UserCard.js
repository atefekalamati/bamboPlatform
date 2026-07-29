import { maskPhoneNumber } from "../utils/phoneNumber.js";

const STATUS_LABELS = Object.freeze({
  active: "فعال",
  inactive: "غیرفعال",
  locked: "قفل‌شده",
});

const createElement = (tagName, className, textContent = "") => {
  const element = document.createElement(tagName);

  element.className = className;
  element.textContent = textContent;

  return element;
};

export const UserCard = ({ user, onEdit }) => {
  const item = document.createElement("li");
  const identity = createElement("div", "user-card__identity");
  const name = createElement("h2", "user-card__name", user.fullName);
  const phone = createElement(
    "span",
    "user-card__phone",
    maskPhoneNumber(user.phoneNumber),
  );
  const role = createElement("span", "user-card__role", user.roleName);
  const status = createElement(
    "span",
    `status-badge status-badge--${user.status}`,
    STATUS_LABELS[user.status] ?? "نامشخص",
  );
  const editButton = createElement("button", "button button--ghost", "ویرایش");

  item.className = "user-card";
  editButton.type = "button";
  editButton.addEventListener("click", () => onEdit(user, editButton));

  identity.append(name, phone);
  item.append(identity, role, status, editButton);

  return item;
};

