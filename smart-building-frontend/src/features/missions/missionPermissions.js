const hasPermission = (permissions, permission) =>
  Array.isArray(permissions) && permissions.includes(permission);

const roleNames = (roles) =>
  new Set(
    (Array.isArray(roles) ? roles : [])
      .map((role) => (typeof role === "string" ? role : role?.name))
      .filter(Boolean),
  );

export const canManageMissionAssignments = (permissions, roles = []) => {
  const names = roleNames(roles);
  const isRestrictedCaptureExpert =
    names.has("capture_expert") &&
    !names.has("operations") &&
    !names.has("super_admin");

  return (
    !isRestrictedCaptureExpert &&
    hasPermission(permissions, "missions.manage") &&
    hasPermission(permissions, "missions.assign")
  );
};

export const canAcceptMissionAssignment = ({
  currentUserId,
  expertUserId,
  permissions,
  roles = [],
}) =>
  Number(currentUserId) === Number(expertUserId) ||
  canManageMissionAssignments(permissions, roles);

