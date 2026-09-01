const NAVIGABLE_STAGE_STATUSES = new Set([
  "open",
  "submitted",
  "needs_revision",
  "approved",
]);

export const getStageRoute = (pilotId, stage) =>
  Number.isInteger(stage?.number) &&
  stage.number >= 1 &&
  stage.number <= 19 &&
  NAVIGABLE_STAGE_STATUSES.has(stage.status)
    ? `#/pilots/${pilotId}/stages/${stage.number}`
    : null;
