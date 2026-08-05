export const USER_STATUS_FILTERS = Object.freeze({
  all: "همه",
  active: "فعال",
  inactive: "غیرفعال",
});

export const matchesUserStatus = (user, statusFilter) => {
  if (statusFilter === "active") return user.isActive === true;
  if (statusFilter === "inactive") return user.isActive === false;
  return true;
};

