import { sessionStore } from "./sessionStore.js";

const THEME_KEY = "bambo_theme";
const DARK_THEME = "dark";
const LIGHT_THEME = "light";

const applyTheme = (theme) => {
  document.documentElement.setAttribute("data-theme", theme);
};

const isTheme = (theme) => theme === DARK_THEME || theme === LIGHT_THEME;
const userThemeKey = (userId) => userId == null ? THEME_KEY : `${THEME_KEY}:user:${userId}`;

const getPreferredTheme = (userId = sessionStore.getCurrentUser()?.id) => {
  const stored = window.localStorage.getItem(userThemeKey(userId));
  if (isTheme(stored)) return stored;
  const legacyTheme = window.localStorage.getItem(THEME_KEY);
  if (isTheme(legacyTheme)) return legacyTheme;
  const prefersDark = window.matchMedia?.(
    "(prefers-color-scheme: dark)",
  ).matches;
  return prefersDark ? DARK_THEME : LIGHT_THEME;
};

export const themeStore = Object.freeze({
  DARK_THEME,
  LIGHT_THEME,
  init: (userId = sessionStore.getCurrentUser()?.id) => {
    const theme = getPreferredTheme(userId);
    applyTheme(theme);
    return theme;
  },
  getTheme: () =>
    document.documentElement.getAttribute("data-theme") || LIGHT_THEME,
  setTheme: (theme, userId = sessionStore.getCurrentUser()?.id) => {
    if (!isTheme(theme)) return;
    applyTheme(theme);
    window.localStorage.setItem(userThemeKey(userId), theme);
  },
  syncFromServer: (theme, userId = sessionStore.getCurrentUser()?.id) => {
    const localTheme = window.localStorage.getItem(userThemeKey(userId));
    if (isTheme(localTheme)) return themeStore.init(userId);
    if (isTheme(theme)) themeStore.setTheme(theme, userId);
    return themeStore.getTheme();
  },
  toggle: () => {
    const next =
      themeStore.getTheme() === DARK_THEME ? LIGHT_THEME : DARK_THEME;
    themeStore.setTheme(next, sessionStore.getCurrentUser()?.id);
    return next;
  },
});
