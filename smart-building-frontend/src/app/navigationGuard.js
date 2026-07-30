let navigationGuard = null;

export const setNavigationGuard = (guard) => {
  navigationGuard = guard;
};

export const clearNavigationGuard = () => {
  navigationGuard = null;
};

export const hasNavigationGuard = () => Boolean(navigationGuard);

export const canLeaveCurrentPage = () => navigationGuard?.() ?? true;

