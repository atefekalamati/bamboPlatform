import { PRIMARY_NAVIGATION } from "../constants/routes.js";

const createNavigation = (currentRoute) => {
  const navigation = document.createElement("nav");
  const list = document.createElement("ul");

  navigation.className = "sidebar__navigation";
  navigation.setAttribute("aria-label", "منوی اصلی");
  list.className = "sidebar__list";

  PRIMARY_NAVIGATION.forEach(({ label, href, isAvailable = false }) => {
    const item = document.createElement("li");
    const navigationItem = document.createElement(isAvailable ? "a" : "span");
    const isActive = href === currentRoute;

    navigationItem.className = "sidebar__link";
    navigationItem.textContent = label;

    if (isAvailable) {
      navigationItem.href = href;
    } else {
      navigationItem.classList.add("sidebar__link--disabled");
      navigationItem.setAttribute("aria-disabled", "true");
    }

    if (isActive) {
      navigationItem.classList.add("sidebar__link--active");
      navigationItem.setAttribute("aria-current", "page");
    }

    item.append(navigationItem);
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

const createHeader = () => {
  const header = document.createElement("header");
  const title = document.createElement("span");
  const status = document.createElement("span");

  header.className = "app-header";
  title.className = "app-header__title";
  title.textContent = "مدیریت پایلوت";

  status.className = "status-badge";
  status.textContent = "نسخه پایه";

  header.append(title, status);

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

