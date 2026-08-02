import { request } from "./httpClient.js";

const mapPermission = (permission) => ({
  id: permission.id,
  code: permission.code,
  groupName: permission.group_name,
  description: permission.description,
  isSensitive: permission.is_sensitive,
});

const mapRole = (role) => ({
  id: role.id,
  name: role.name,
  displayName: role.display_name,
  isSystem: role.is_system,
  isActive: role.is_active,
  permissions: role.permissions.map(mapPermission),
});

export const roleService = Object.freeze({
  getRoles: async () => (await request("/roles")).map(mapRole),
  getPermissions: async () =>
    (await request("/roles/permissions")).map(mapPermission),
  createRole: async ({ name, displayName }) =>
    mapRole(
      await request("/roles", {
        method: "POST",
        body: JSON.stringify({ name, display_name: displayName }),
      }),
    ),
  updateRole: async (roleId, payload) =>
    mapRole(
      await request(`/roles/${roleId}`, {
        method: "PUT",
        body: JSON.stringify({
          ...(payload.name !== undefined ? { name: payload.name } : {}),
          ...(payload.displayName !== undefined ? { display_name: payload.displayName } : {}),
          ...(payload.isActive !== undefined ? { is_active: payload.isActive } : {}),
        }),
      }),
    ),
  cloneRole: async (roleId, { name, displayName }) =>
    mapRole(
      await request(`/roles/${roleId}/clone`, {
        method: "POST",
        body: JSON.stringify({ name, display_name: displayName }),
      }),
    ),
  getAccessPreview: (roleId) => request(`/roles/${roleId}/access-preview`),
  updatePermissions: async (roleId, { permissionCodes, confirmed }) =>
    mapRole(
      await request(`/roles/${roleId}/permissions`, {
        method: "PUT",
        body: JSON.stringify({
          permission_codes: permissionCodes,
          confirmed,
        }),
      }),
    ),
  deleteRole: (roleId) =>
    request(`/roles/${roleId}`, { method: "DELETE" }),
});
