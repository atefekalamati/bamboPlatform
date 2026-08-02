const API_ERROR_EVENT = "bambo:api-error";
const AUTH_REQUIRED_EVENT = "bambo:auth-required";

const toCamelCase = (value) =>
  value.replace(/_([a-z0-9])/g, (_, character) => character.toUpperCase());

const fieldCandidates = (field) => {
  const parts = String(field).split(".").filter(Boolean);
  const lastPart = parts.at(-1) ?? "";
  return [...new Set([field, lastPart, toCamelCase(lastPart)])].filter(Boolean);
};

const matchingControls = (root, field) => {
  const controls = root.querySelectorAll("input, select, textarea");
  const candidates = fieldCandidates(field);

  return [...controls].filter((control) =>
    candidates.some(
      (candidate) =>
        control.name === candidate ||
        control.id === candidate ||
        control.dataset.field === candidate,
    ),
  );
};

export const markApiErrorFields = (root, error) => {
  if (!root || !Array.isArray(error?.errors)) return [];

  const invalidControls = error.errors.flatMap(({ field }) =>
    field ? matchingControls(root, field) : [],
  );

  [...new Set(invalidControls)].forEach((control) =>
    control.setAttribute("aria-invalid", "true"),
  );

  return invalidControls;
};

export const reportApiError = (error) => {
  window.dispatchEvent(new CustomEvent(API_ERROR_EVENT, { detail: error }));
};

export const reportAuthenticationRequired = (error) => {
  window.dispatchEvent(new CustomEvent(AUTH_REQUIRED_EVENT, { detail: error }));
};

export const onApiError = (listener) => {
  window.addEventListener(API_ERROR_EVENT, listener);
  return () => window.removeEventListener(API_ERROR_EVENT, listener);
};

export const onAuthenticationRequired = (listener) => {
  window.addEventListener(AUTH_REQUIRED_EVENT, listener);
  return () => window.removeEventListener(AUTH_REQUIRED_EVENT, listener);
};
