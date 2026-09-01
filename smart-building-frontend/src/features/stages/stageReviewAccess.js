const includesStage = (access, action, stageNumber) =>
  Array.isArray(access?.[action]) && access[action].includes(Number(stageNumber));

export const getStageReviewAccess = (user, stageNumber) => {
  const permissions = user?.permissions ?? [];
  const stageAccess = user?.stageAccess;
  return {
    canApprove:
      permissions.includes("gate_approval.approve") &&
      includesStage(stageAccess, "approve", stageNumber),
    canReject:
      permissions.includes("gate_approval.reject") &&
      includesStage(stageAccess, "reject", stageNumber),
  };
};
