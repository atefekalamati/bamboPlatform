const THEME_KEY = "bambo_theme";
const DARK_THEME = "dark";
const LIGHT_THEME = "light";

const applyTheme = (theme) => {
  document.documentElement.setAttribute("data-theme", theme);
};

const getPreferredTheme = () => {
  const stored = window.localStorage.getItem(THEME_KEY);
  if (stored === DARK_THEME || stored === LIGHT_THEME) return stored;
  const prefersDark = window.matchMedia?.(
    "(prefers-color-scheme: dark)",
  ).matches;
  return prefersDark ? DARK_THEME : LIGHT_THEME;
};

export const themeStore = Object.freeze({
  DARK_THEME,
  LIGHT_THEME,
  init: () => {
    const theme = getPreferredTheme();
    applyTheme(theme);
    return theme;
  },
  getTheme: () =>
    document.documentElement.getAttribute("data-theme") || LIGHT_THEME,
  setTheme: (theme) => {
    applyTheme(theme);
    window.localStorage.setItem(THEME_KEY, theme);
  },
  syncFromServer: (theme) => {
    if (theme === DARK_THEME || theme === LIGHT_THEME) {
      themeStore.setTheme(theme);
    }
  },
  toggle: () => {
    const next =
      themeStore.getTheme() === DARK_THEME ? LIGHT_THEME : DARK_THEME;
    themeStore.setTheme(next);
    return next;
  },
});
