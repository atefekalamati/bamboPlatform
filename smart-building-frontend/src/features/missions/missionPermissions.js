const hasPermission = (permissions, permission) =>
  Array.isArray(permissions) && permissions.includes(permission);

export const canManageMissionAssignments = (permissions) =>
  hasPermission(permissions, "missions.manage") &&
  hasPermission(permissions, "missions.assign");

export const canAcceptMissionAssignment = ({
  currentUserId,
  expertUserId,
  permissions,
}) =>
  Number(currentUserId) === Number(expertUserId) ||
  canManageMissionAssignments(permissions);

