import { ROUTES } from "../constants/routes.js";
import { AppShell } from "../layouts/AppShell.js";
import { DashboardPage } from "../pages/DashboardPage.js";
import { PilotDetailsPage } from "../pages/PilotDetailsPage.js";
import { PilotsPage } from "../pages/PilotsPage.js";
import { StageOnePage } from "../pages/StageOnePage.js";
import { UsersPage } from "../pages/UsersPage.js";
import {
  canLeaveCurrentPage,
  clearNavigationGuard,
  hasNavigationGuard,
} from "./navigationGuard.js";

const ROUTE_FACTORIES = Object.freeze({
  [ROUTES.dashboard]: DashboardPage,
  [ROUTES.pilots]: PilotsPage,
  [ROUTES.users]: UsersPage,
});

const getCurrentRoute = () => window.location.hash || ROUTES.dashboard;

const resolveRoute = (currentRoute) => {
  const exactPageFactory = ROUTE_FACTORIES[currentRoute];

  if (exactPageFactory) {
    return {
      page: exactPageFactory(),
      navigationRoute: currentRoute,
    };
  }

  const pilotDetailsMatch = currentRoute.match(/^#\/pilots\/([^/]+)$/);
  const stageOneMatch = currentRoute.match(
    /^#\/pilots\/([^/]+)\/stages\/1$/,
  );

  if (stageOneMatch) {
    return {
      page: StageOnePage({ pilotId: stageOneMatch[1] }),
      navigationRoute: ROUTES.pilots,
    };
  }

  if (pilotDetailsMatch) {
    return {
      page: PilotDetailsPage({ pilotId: pilotDetailsMatch[1] }),
      navigationRoute: ROUTES.pilots,
    };
  }

  return {
    page: DashboardPage(),
    navigationRoute: ROUTES.dashboard,
  };
};

const renderRoute = (appRoot) => {
  const currentRoute = getCurrentRoute();
  const resolvedRoute = resolveRoute(currentRoute);

  appRoot.replaceChildren(
    AppShell({
      content: resolvedRoute.page,
      currentRoute: resolvedRoute.navigationRoute,
    }),
  );
};

export const startRouter = (appRoot) => {
  let renderedRoute = getCurrentRoute();
  let isRestoringRoute = false;

  renderRoute(appRoot);
  window.addEventListener("hashchange", () => {
    if (isRestoringRoute) {
      isRestoringRoute = false;
      return;
    }

    if (!canLeaveCurrentPage()) {
      isRestoringRoute = true;
      window.location.hash = renderedRoute;
      return;
    }

    clearNavigationGuard();
    renderedRoute = getCurrentRoute();
    renderRoute(appRoot);
  });
  window.addEventListener("beforeunload", (event) => {
    if (!hasNavigationGuard()) return;

    event.preventDefault();
    event.returnValue = "";
  });
};
