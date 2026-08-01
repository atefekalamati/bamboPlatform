import { ROUTES } from "../constants/routes.js";
import { AppShell } from "../layouts/AppShell.js";
import { DashboardPage } from "../pages/DashboardPage.js";
import { PilotDetailsPage } from "../pages/PilotDetailsPage.js";
import { PilotsPage } from "../pages/PilotsPage.js";
import { RolesPage } from "../pages/RolesPage.js";
import { StageOnePage } from "../pages/StageOnePage.js";
import { StageTwoPage } from "../pages/StageTwoPage.js";
import { StageThreePage } from "../pages/StageThreePage.js";
import { StageFourPage } from "../pages/StageFourPage.js";
import { StageFivePage } from "../pages/StageFivePage.js";
import { StageSixPage } from "../pages/StageSixPage.js";
import { StageSevenPage } from "../pages/StageSevenPage.js";
import { StageEightPage } from "../pages/StageEightPage.js";
import { StageNinePage } from "../pages/StageNinePage.js";
import { StageTenPage } from "../pages/StageTenPage.js";
import { StageElevenPage } from "../pages/StageElevenPage.js";
import { StageTwelvePage } from "../pages/StageTwelvePage.js";
import { StageThirteenPage } from "../pages/StageThirteenPage.js";
import { StageFourteenPage } from "../pages/StageFourteenPage.js";
import { StageFifteenPage } from "../pages/StageFifteenPage.js";
import { StageSixteenPage } from "../pages/StageSixteenPage.js";
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
  const stageFourMatch = currentRoute.match(
    /^#\/pilots\/([^/]+)\/stages\/4$/,
  );
  const stageFiveMatch = currentRoute.match(
    /^#\/pilots\/([^/]+)\/stages\/5$/,
  );
  const stageSixMatch = currentRoute.match(
    /^#\/pilots\/([^/]+)\/stages\/6$/,
  );
  const stageSevenMatch = currentRoute.match(
    /^#\/pilots\/([^/]+)\/stages\/7$/,
  );
  const stageEightMatch = currentRoute.match(
    /^#\/pilots\/([^/]+)\/stages\/8$/,
  );
  const stageNineMatch = currentRoute.match(
    /^#\/pilots\/([^/]+)\/stages\/9$/,
  );
  const stageTenMatch = currentRoute.match(
    /^#\/pilots\/([^/]+)\/stages\/10$/,
  );
  const stageElevenMatch = currentRoute.match(
    /^#\/pilots\/([^/]+)\/stages\/11$/,
  );
  const stageTwelveMatch = currentRoute.match(
    /^#\/pilots\/([^/]+)\/stages\/12$/,
  );
  const stageThirteenMatch = currentRoute.match(
    /^#\/pilots\/([^/]+)\/stages\/13$/,
  );
  const stageFourteenMatch = currentRoute.match(
    /^#\/pilots\/([^/]+)\/stages\/14$/,
  );
  const stageFifteenMatch = currentRoute.match(
    /^#\/pilots\/([^/]+)\/stages\/15$/,
  );
  const stageSixteenMatch = currentRoute.match(
    /^#\/pilots\/([^/]+)\/stages\/16$/,
  );

  if (stageSixteenMatch) {
    return {
      page: StageSixteenPage({ pilotId: stageSixteenMatch[1] }),
      navigationRoute: ROUTES.pilots,
    };
  }

  if (stageFifteenMatch) {
    return {
      page: StageFifteenPage({ pilotId: stageFifteenMatch[1] }),
      navigationRoute: ROUTES.pilots,
    };
  }

  if (stageFourteenMatch) {
    return {
      page: StageFourteenPage({ pilotId: stageFourteenMatch[1] }),
      navigationRoute: ROUTES.pilots,
    };
  }

  if (stageThirteenMatch) {
    return {
      page: StageThirteenPage({ pilotId: stageThirteenMatch[1] }),
      navigationRoute: ROUTES.pilots,
    };
  }

  if (stageTwelveMatch) {
    return {
      page: StageTwelvePage({ pilotId: stageTwelveMatch[1] }),
      navigationRoute: ROUTES.pilots,
    };
  }

  if (stageElevenMatch) {
    return {
      page: StageElevenPage({ pilotId: stageElevenMatch[1] }),
      navigationRoute: ROUTES.pilots,
    };
  }

  if (stageTenMatch) {
    return {
      page: StageTenPage({ pilotId: stageTenMatch[1] }),
      navigationRoute: ROUTES.pilots,
    };
  }

  if (stageNineMatch) {
    return {
      page: StageNinePage({ pilotId: stageNineMatch[1] }),
      navigationRoute: ROUTES.pilots,
    };
  }

  if (stageEightMatch) {
    return {
      page: StageEightPage({ pilotId: stageEightMatch[1] }),
      navigationRoute: ROUTES.pilots,
    };
  }

  if (stageSevenMatch) {
    return {
      page: StageSevenPage({ pilotId: stageSevenMatch[1] }),
      navigationRoute: ROUTES.pilots,
    };
  }

  if (stageSixMatch) {
    return {
      page: StageSixPage({ pilotId: stageSixMatch[1] }),
      navigationRoute: ROUTES.pilots,
    };
  }

  if (stageFiveMatch) {
    return {
      page: StageFivePage({ pilotId: stageFiveMatch[1] }),
      navigationRoute: ROUTES.pilots,
    };
  }

  if (stageFourMatch) {
    return {
      page: StageFourPage({ pilotId: stageFourMatch[1] }),
      navigationRoute: ROUTES.pilots,
    };
  }

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
