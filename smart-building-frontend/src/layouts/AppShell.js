import { sessionStore } from "../app/sessionStore.js";
import { themeStore } from "../app/themeStore.js";
import { PRIMARY_NAVIGATION } from "../constants/routes.js";
import { authService } from "../services/authService.js";
import { preferenceService } from "../services/preferenceService.js";
import { NotificationCenter } from "../components/NotificationCenter.js";
import { notificationStore } from "../app/notificationStore.js";

const SVG_NAMESPACE = "http://www.w3.org/2000/svg";

const createLogoutIcon = () => {
  const icon = document.createElementNS(SVG_NAMESPACE, "svg");
  const paths = [
    "M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4",
    "m16 17 5-5-5-5",
    "M21 12H9",
  ];

  icon.setAttribute("viewBox", "0 0 24 24");
  icon.setAttribute("aria-hidden", "true");
  icon.setAttribute("focusable", "false");

  paths.forEach((pathData) => {
    const path = document.createElementNS(SVG_NAMESPACE, "path");
    path.setAttribute("d", pathData);
    icon.append(path);
  });

  return icon;
};

const createNavigation = (currentRoute) => {
  const navigation = document.createElement("nav");
  const list = document.createElement("ul");
  navigation.className = "sidebar__navigation";
  navigation.setAttribute("aria-label", "منوی اصلی");
  list.className = "sidebar__list";

  const permissions = sessionStore.getCurrentUser()?.permissions ?? [];
  PRIMARY_NAVIGATION.forEach(({ label, href, isAvailable = false, permission }) => {
    if (permission && !permissions.includes(permission)) return;
    const item = document.createElement("li");
    const link = document.createElement(isAvailable ? "a" : "span");
    link.className = "sidebar__link";
    link.textContent = label;
    if (isAvailable) link.href = href;
    else {
      link.classList.add("sidebar__link--disabled");
      link.setAttribute("aria-disabled", "true");
    }
    if (href === currentRoute) {
      link.classList.add("sidebar__link--active");
      link.setAttribute("aria-current", "page");
    }
    item.append(link);
    list.append(item);
  });
  navigation.append(list);
  return navigation;
};

const createSidebar = (currentRoute) => {
  const sidebar = document.createElement("aside");
  const logo = document.createElement("img");
  sidebar.className = "sidebar";
  logo.className = "sidebar__logo";
  logo.src = "./src/assets/images/Persian Logo Final.svg";
  logo.alt = "BAMBO";
  sidebar.append(logo, createNavigation(currentRoute));
  return sidebar;
};

const createThemeToggle = () => {
  const toggle = document.createElement("button");
  toggle.type = "button";
  toggle.className = "theme-toggle";

  const syncState = () => {
    const isDark = themeStore.getTheme() === themeStore.DARK_THEME;
    toggle.textContent = '◐';
    toggle.setAttribute(
      "aria-label",
      isDark ? "فعال‌سازی پوسته روشن" : "فعال‌سازی پوسته تیره",
    );
    toggle.setAttribute("aria-pressed", String(isDark));
  };

  toggle.addEventListener("click", async () => {
    const theme = themeStore.toggle();
    syncState();
    await preferenceService.updatePreferences({ theme }).catch(() => null);
  });

  syncState();
  return toggle;
};

const createMenuIcon = () => {
  const icon = document.createElementNS(SVG_NAMESPACE, "svg");
  icon.setAttribute("viewBox", "0 0 24 24");
  icon.setAttribute("aria-hidden", "true");
  ["M4 6h16", "M4 12h16", "M4 18h16"].forEach((value) => {
    const path = document.createElementNS(SVG_NAMESPACE, "path");
    path.setAttribute("d", value);
    icon.append(path);
  });
  return icon;
};

const createHeader = ({ onMenuToggle }) => {
  const header = document.createElement("header");
  const primary = document.createElement("div");
  const menu = document.createElement("button");
  const title = document.createElement("span");
  const account = document.createElement("div");
  const userName = document.createElement("span");
  const logout = document.createElement("button");
  const user = sessionStore.getCurrentUser();
  header.className = "app-header";
  primary.className = "app-header__primary";
  menu.className = "button button--ghost app-header__menu";
  menu.type = "button";
  menu.setAttribute("aria-label", "بازکردن منوی اصلی");
  menu.setAttribute("aria-expanded", "false");
  menu.setAttribute("aria-controls", "primary-sidebar");
  menu.append(createMenuIcon());
  menu.addEventListener("click", () => onMenuToggle(menu));
  title.className = "app-header__title";
  title.textContent = "مدیریت پایلوت";
  account.className = "app-header__account";
  userName.textContent = user?.display_name ?? "";
  logout.className = "button button--ghost app-header__logout";
  logout.type = "button";
  logout.title = "خروج";
  logout.setAttribute("aria-label", "خروج");
  logout.append(createLogoutIcon());
  logout.addEventListener("click", async () => {
    logout.disabled = true;
    notificationStore.stop();
    await authService.logout();
    window.location.reload();
  });
  const permissions = user?.permissions ?? [];
  if (permissions.includes("notifications.read")) account.append(NotificationCenter());
  account.append(userName, createThemeToggle(), logout);
  primary.append(menu, title);
  header.append(primary, account);
  return header;
};

export const AppShell = ({ content, currentRoute }) => {
  const shell = document.createElement("div");
  const workspace = document.createElement("div");
  const main = document.createElement("main");
  const sidebar = createSidebar(currentRoute);
  const backdrop = document.createElement("button");
  let menuButton = null;

  const setMenuOpen = (isOpen) => {
    shell.classList.toggle("app-shell--menu-open", isOpen);
    menuButton?.setAttribute("aria-expanded", String(isOpen));
    menuButton?.setAttribute("aria-label", isOpen ? "بستن منوی اصلی" : "بازکردن منوی اصلی");
    if (isOpen) sidebar.querySelector("a:not([aria-disabled='true'])")?.focus();
    else menuButton?.focus();
  };

  shell.className = "app-shell";
  sidebar.id = "primary-sidebar";
  backdrop.className = "sidebar-backdrop";
  backdrop.type = "button";
  backdrop.tabIndex = -1;
  backdrop.setAttribute("aria-label", "بستن منوی اصلی");
  backdrop.addEventListener("click", () => setMenuOpen(false));
  sidebar.addEventListener("click", (event) => {
    if (event.target.closest("a")) setMenuOpen(false);
  });
  shell.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && shell.classList.contains("app-shell--menu-open")) setMenuOpen(false);
  });
  workspace.className = "app-workspace";
  main.id = "main-content";
  main.className = "main-content";
  main.tabIndex = -1;
  main.append(content);
  const header = createHeader({ onMenuToggle: (button) => {
    menuButton = button;
    setMenuOpen(!shell.classList.contains("app-shell--menu-open"));
  } });
  menuButton = header.querySelector(".app-header__menu");
  workspace.append(header, main);
  shell.append(sidebar, backdrop, workspace);
  return shell;
};
