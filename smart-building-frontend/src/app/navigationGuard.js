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

const isEditableStageControl = (target) => {
  if (!(target instanceof HTMLInputElement || target instanceof HTMLSelectElement || target instanceof HTMLTextAreaElement)) return false;
  if (target.disabled || target.readOnly || target.dataset.navigationGuardIgnore === "true") return false;
  return !["button", "submit", "reset", "hidden"].includes(target.type);
};

export const installStageNavigationGuard = (page, route) => {
  if (!/^#\/pilots\/[^/]+\/stages\/\d+$/.test(route.split("?")[0])) return () => {};

  let dirty = false;
  const markDirty = (event) => {
    if (!isEditableStageControl(event.target)) return;
    dirty = true;
    setNavigationGuard(
      createUnsavedChangesGuard(
        "تغییرات این مرحله هنوز ذخیره نشده است. در صورت خروج، اطلاعات واردشده از بین می‌رود.",
      ),
    );
  };
  const resetAfterRender = () => {
    if (!dirty) return;
    dirty = false;
    clearNavigationGuard();
  };
  const observer = new MutationObserver(resetAfterRender);
  observer.observe(page, { childList: true });
  page.addEventListener("input", markDirty, true);
  page.addEventListener("change", markDirty, true);

  return () => {
    observer.disconnect();
    page.removeEventListener("input", markDirty, true);
    page.removeEventListener("change", markDirty, true);
    if (dirty) clearNavigationGuard();
  };
};

