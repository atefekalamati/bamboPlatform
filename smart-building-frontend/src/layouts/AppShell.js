import { sessionStore } from "../app/sessionStore.js";
import { themeStore } from "../app/themeStore.js";
import { PRIMARY_NAVIGATION } from "../constants/routes.js";
import { authService } from "../services/authService.js";

const createNavigation = (currentRoute) => {
  const navigation = document.createElement("nav");
  const list = document.createElement("ul");
  navigation.className = "sidebar__navigation";
  navigation.setAttribute("aria-label", "منوی اصلی");
  list.className = "sidebar__list";

  PRIMARY_NAVIGATION.forEach(({ label, href, isAvailable = false }) => {
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

  toggle.addEventListener("click", () => {
    themeStore.toggle();
    syncState();
  });

  syncState();
  return toggle;
};

const createHeader = () => {
  const header = document.createElement("header");
  const title = document.createElement("span");
  const account = document.createElement("div");
  const userName = document.createElement("span");
  const logout = document.createElement("button");
  const user = sessionStore.getCurrentUser();
  header.className = "app-header";
  title.className = "app-header__title";
  title.textContent = "مدیریت پایلوت";
  account.className = "app-header__account";
  userName.textContent = user?.display_name ?? "";
  logout.className = "button button--ghost";
  logout.type = "button";
  logout.textContent = "خروج";
  logout.addEventListener("click", async () => {
    logout.disabled = true;
    await authService.logout();
    window.location.reload();
  });
  account.append(userName, createThemeToggle(), logout);
  header.append(title, account);
  return header;
};

export const AppShell = ({ content, currentRoute }) => {
  const shell = document.createElement("div");
  const workspace = document.createElement("div");
  const main = document.createElement("main");
  shell.className = "app-shell";
  workspace.className = "app-workspace";
  main.id = "main-content";
  main.className = "main-content";
  main.tabIndex = -1;
  main.append(content);
  workspace.append(createHeader(), main);
  shell.append(createSidebar(currentRoute), workspace);
  return shell;
};