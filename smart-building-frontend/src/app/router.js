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
import { StageSeventeenPage } from "../pages/StageSeventeenPage.js";
import { StageEighteenPage } from "../pages/StageEighteenPage.js";
import { StageNineteenPage } from "../pages/StageNineteenPage.js";
import { UsersPage } from "../pages/UsersPage.js";
import { NotificationsPage } from "../pages/NotificationsPage.js";
import { NotificationPreferencesPage } from "../pages/NotificationPreferencesPage.js";
import { IncidentsPage } from "../pages/IncidentsPage.js";
import { IncidentCreatePage } from "../pages/IncidentCreatePage.js";
import { IncidentDetailPage } from "../pages/IncidentDetailPage.js";
import {
  ReportsOverviewPage,
  PilotProgressReportPage,
  ActionsReportPage,
  KpiReportPage,
  IncidentReportPage,
  PilotOnePageReportPage,
} from "../pages/ReportsPage.js";
import {
  canLeaveCurrentPage,
  clearNavigationGuard,
  hasNavigationGuard,
  installStageNavigationGuard,
} from "./navigationGuard.js";
import { sessionStore } from "./sessionStore.js";
import { accessDeniedReason, canAccessRoute } from "./routePermissions.js";
import { installStageActionLayout } from "./stageActionLayout.js";
import { matchStageRoute, normalizeRoutePath } from "./routeMatcher.js";

const accessDeniedPage = (route, permissions = [], roles = []) => {
  const reason = accessDeniedReason(route, permissions, roles);
  const page = document.createElement("main");
  const heading = document.createElement("h1");
  const message = document.createElement("p");
  page.className = "page error-state";
  heading.textContent = reason.title;
  message.textContent = reason.message;
  page.append(heading, message);
  if (reason.returnRoute) {
    const back = document.createElement("a");
    back.className = "button button--primary";
    back.href = reason.returnRoute;
    back.textContent = "بازگشت به نمای کلی";
    page.append(back);
  }
  return page;
};

const notFoundPage = () => {
  const page = document.createElement("main");
  const heading = document.createElement("h1");
  const message = document.createElement("p");
  const back = document.createElement("a");
  page.className = "page error-state";
  heading.textContent = "صفحه پیدا نشد";
  message.className = "error-state__message";
  message.textContent = "نشانی واردشده معتبر نیست یا این صفحه دیگر در دسترس نیست.";
  back.className = "button button--primary";
  back.href = ROUTES.dashboard;
  back.textContent = "بازگشت به نمای کلی";
  page.append(heading, message, back);
  return page;
};

const ROUTE_FACTORIES = Object.freeze({
  [ROUTES.dashboard]: DashboardPage,
  [ROUTES.pilots]: PilotsPage,
  [ROUTES.users]: UsersPage,
  [ROUTES.roles]: RolesPage,
  [ROUTES.notifications]: NotificationsPage,
  [ROUTES.notificationSettings]: NotificationPreferencesPage,
  [ROUTES.incidents]: IncidentsPage,
  [ROUTES.reports]: ReportsOverviewPage,
  [ROUTES.reportPilots]: PilotProgressReportPage,
  [ROUTES.reportActions]: ActionsReportPage,
  [ROUTES.reportKpis]: KpiReportPage,
  [ROUTES.reportIncidents]: IncidentReportPage,
});

const getCurrentRoute = () => window.location.hash || ROUTES.dashboard;

const resolveRoute = (currentRoute) => {
  const user = sessionStore.getCurrentUser();
  const permissions = user?.permissions ?? [];
  const roles = user?.roles ?? [];
  if (!canAccessRoute(currentRoute, permissions, roles)) {
    return { page: accessDeniedPage(currentRoute, permissions, roles), navigationRoute: "" };
  }
  const routePath = normalizeRoutePath(currentRoute);
  const exactPageFactory = ROUTE_FACTORIES[routePath];

  if (exactPageFactory) {
    return {
      page: exactPageFactory(),
      navigationRoute: routePath.startsWith("#/reports") ? ROUTES.reports : routePath,
    };
  }

  const reportPilotMatch = routePath.match(/^#\/reports\/pilots\/([^/?#]+)$/);
  if (reportPilotMatch) {
    return { page: PilotOnePageReportPage({ pilotId: reportPilotMatch[1] }), navigationRoute: ROUTES.reports };
  }

  const pilotDetailsMatch = routePath.match(/^#\/pilots\/([^/]+)$/);
  const incidentCreateMatch = routePath.match(/^#\/pilots\/([^/]+)\/incidents\/new$/);
  const incidentDetailMatch = routePath.match(/^#\/incidents\/([^/?#]+)$/);
  const notificationDetailsMatch = routePath.match(/^#\/notifications\/([^/?#]+)$/);
  const stageMatch = matchStageRoute(routePath);

  if (incidentCreateMatch) {
    return {
      page: IncidentCreatePage({ pilotId: incidentCreateMatch[1] }),
      navigationRoute: ROUTES.incidents,
    };
  }

  if (incidentDetailMatch) {
    return {
      page: IncidentDetailPage({ incidentId: incidentDetailMatch[1] }),
      navigationRoute: ROUTES.incidents,
    };
  }

  if (notificationDetailsMatch) {
    return {
      page: NotificationsPage({ notificationId: decodeURIComponent(notificationDetailsMatch[1]) }),
      navigationRoute: ROUTES.notifications,
    };
  }

  if (stageMatch) {
    const stagePages = [
      StageOnePage, StageTwoPage, StageThreePage, StageFourPage, StageFivePage,
      StageSixPage, StageSevenPage, StageEightPage, StageNinePage, StageTenPage,
      StageElevenPage, StageTwelvePage, StageThirteenPage, StageFourteenPage,
      StageFifteenPage, StageSixteenPage, StageSeventeenPage, StageEighteenPage,
      StageNineteenPage,
    ];
    return {
      page: stagePages[stageMatch.stageNumber - 1]({ pilotId: stageMatch.pilotId }),
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
    page: notFoundPage(),
    navigationRoute: "",
  };
};

let cleanupStageNavigationGuard = () => {};
let cleanupStageActionLayout = () => {};
let cleanupAppShell = () => {};

const renderRoute = (appRoot) => {
  cleanupStageNavigationGuard();
  cleanupStageActionLayout();
  cleanupAppShell();
  const currentRoute = getCurrentRoute();
  const resolvedRoute = resolveRoute(currentRoute);
  cleanupStageNavigationGuard = installStageNavigationGuard(
    resolvedRoute.page,
    currentRoute,
  );
  cleanupStageActionLayout = installStageActionLayout(
    resolvedRoute.page,
    currentRoute,
  );

  const shell = AppShell({
    content: resolvedRoute.page,
    currentRoute: resolvedRoute.navigationRoute,
  });
  cleanupAppShell = () => shell.cleanup?.();
  appRoot.replaceChildren(shell);
};

export const startRouter = (appRoot) => {
  let renderedRoute = getCurrentRoute();
  let isRestoringRoute = false;

  renderRoute(appRoot);
  const handleHashChange = async () => {
    if (isRestoringRoute) {
      isRestoringRoute = false;
      return;
    }

    const nextRoute = getCurrentRoute();
    if (!(await canLeaveCurrentPage())) {
      isRestoringRoute = true;
      window.location.hash = renderedRoute;
      return;
    }

    clearNavigationGuard();
    renderedRoute = nextRoute;
    renderRoute(appRoot);
  };
  const handleBeforeUnload = (event) => {
    if (!hasNavigationGuard()) return;

    event.preventDefault();
    event.returnValue = "";
  };
  window.addEventListener("hashchange", handleHashChange);
  window.addEventListener("beforeunload", handleBeforeUnload);
  return () => {
    window.removeEventListener("hashchange", handleHashChange);
    window.removeEventListener("beforeunload", handleBeforeUnload);
    cleanupStageNavigationGuard();
    cleanupStageActionLayout();
    cleanupAppShell();
    cleanupAppShell = () => {};
    clearNavigationGuard();
  };
};
