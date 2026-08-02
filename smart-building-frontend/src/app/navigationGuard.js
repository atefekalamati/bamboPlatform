import { confirmDialog } from "../components/AppDialog.js";

let navigationGuard = null;

export const setNavigationGuard = (guard) => {
  navigationGuard = guard;
};

export const clearNavigationGuard = () => {
  navigationGuard = null;
};

export const hasNavigationGuard = () => Boolean(navigationGuard);

export const canLeaveCurrentPage = async () =>
  (await navigationGuard?.()) ?? true;

export const createUnsavedChangesGuard = (message) => () =>
  confirmDialog({
    title: "تغییرات ذخیره‌نشده",
    message,
    confirmLabel: "خروج بدون ذخیره",
  });

