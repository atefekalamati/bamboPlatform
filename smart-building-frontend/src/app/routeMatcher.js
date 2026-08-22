export const normalizeRoutePath = (route) => String(route || "").split("?")[0];

export const matchStageRoute = (route) => {
  const match = normalizeRoutePath(route).match(
    /^#\/pilots\/([^/?#]+)\/stages\/(1[0-9]|[1-9])$/,
  );
  if (!match) return null;
  return {
    pilotId: match[1],
    stageNumber: Number(match[2]),
  };
};
