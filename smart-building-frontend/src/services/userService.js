import { request } from "./httpClient.js";

const mapRole = (role) => ({
  id: role.id,
  name: role.name,
  displayName: role.display_name,
});

const mapUser = (user) => ({
  id: user.id,
  mobile: user.mobile,
  displayName: user.display_name,
  canEditOwnName: Boolean(user.can_edit_own_name),
  isActive: user.is_active,
  lockedAt: user.locked_at,
  roles: user.roles.map(mapRole),
  permissions: user.permissions,
});

export const userService = Object.freeze({
  getUsers: async () => (await request("/users")).map(mapUser),
  createUser: async ({ mobile, displayName, roleIds, isActive }) =>
    mapUser(
      await request("/users", {
        method: "POST",
        body: JSON.stringify({
          mobile,
          display_name: displayName,
          role_ids: roleIds,
          is_active: isActive,
        }),
      }),
    ),
  updateName: async (userId, displayName) =>
    mapUser(
      await request(`/users/${userId}`, {
        method: "PATCH",
        body: JSON.stringify({ display_name: displayName }),
      }),
    ),
  updateOwnNamePermission: async (userId, canEditOwnName) =>
    mapUser(
      await request(`/users/${userId}/own-name-edit-permission`, {
        method: "PATCH",
        body: JSON.stringify({ can_edit_own_name: canEditOwnName }),
      }),
    ),
  updateRoles: async (userId, roleIds) =>
    mapUser(
      await request(`/users/${userId}/roles`, {
        method: "PUT",
        body: JSON.stringify({ role_ids: roleIds, confirmed: true }),
      }),
    ),
  updateStatus: async (userId, { isActive, reason }) =>
    mapUser(
      await request(`/users/${userId}/status`, {
        method: "PATCH",
        body: JSON.stringify({ is_active: isActive, reason, confirmed: true }),
      }),
    ),
});
