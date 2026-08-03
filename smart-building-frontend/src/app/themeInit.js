(function initializeTheme() {
  const stored = window.localStorage.getItem("bambo_theme");
  const preferredDark = window.matchMedia?.("(prefers-color-scheme: dark)").matches;
  const theme = stored === "dark" || stored === "light" ? stored : preferredDark ? "dark" : "light";
  document.documentElement.setAttribute("data-theme", theme);
})();

