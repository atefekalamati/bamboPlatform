(function initializeTheme() {
  let userId = null;
  try {
    userId = JSON.parse(window.sessionStorage.getItem("bambo_user_summary") || "null")?.id ?? null;
  } catch {
    userId = null;
  }
  const userThemeKey = userId == null ? null : `bambo_theme:user:${userId}`;
  const stored = (userThemeKey && window.localStorage.getItem(userThemeKey))
    || window.localStorage.getItem("bambo_theme");
  const preferredDark = window.matchMedia?.("(prefers-color-scheme: dark)").matches;
  const theme = stored === "dark" || stored === "light" ? stored : preferredDark ? "dark" : "light";
  document.documentElement.setAttribute("data-theme", theme);
})();

