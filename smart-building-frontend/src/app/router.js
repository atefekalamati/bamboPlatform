import { ROUTES } from "../constants/routes.js";
import { AppShell } from "../layouts/AppShell.js";
import { DashboardPage } from "../pages/DashboardPage.js";
import { PilotDetailsPage } from "../pages/PilotDetailsPage.js";
import { PilotsPage } from "../pages/PilotsPage.js";
import { RolesPage } from "../pages/RolesPage.js";
import { StageOnePage } from "../pages/StageOnePage.js";
import { StageTwoPage } from "../pages/StageTwoPage.js";
import { StageThreePage } from "../pages/StageThreePage.js";
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
  [ROUTES.roles]: RolesPage,
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
  const stageTwoMatch = currentRoute.match(
    /^#\/pilots\/([^/]+)\/stages\/2$/,
  );
  const stageThreeMatch = currentRoute.match(
    /^#\/pilots\/([^/]+)\/stages\/3$/,
  );

  if (stageThreeMatch) {
    return {
      page: StageThreePage({ pilotId: stageThreeMatch[1] }),
      navigationRoute: ROUTES.pilots,
    };
  }

  if (stageTwoMatch) {
    return {
      page: StageTwoPage({ pilotId: stageTwoMatch[1] }),
      navigationRoute: ROUTES.pilots,
    };
  }

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
