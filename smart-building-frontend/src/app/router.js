import { ROUTES } from "../constants/routes.js";
import { AppShell } from "../layouts/AppShell.js";
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

const pageLoader = (path, exportName) => async (props) => {
  const module = await import(path);
  return module[exportName](props);
};

const ROUTE_LOADERS = Object.freeze({
  [ROUTES.dashboard]: pageLoader("../pages/DashboardPage.js", "DashboardPage"),
  [ROUTES.pilots]: pageLoader("../pages/PilotsPage.js", "PilotsPage"),
  [ROUTES.users]: pageLoader("../pages/UsersPage.js", "UsersPage"),
  [ROUTES.roles]: pageLoader("../pages/RolesPage.js", "RolesPage"),
  [ROUTES.notifications]: pageLoader("../pages/NotificationsPage.js", "NotificationsPage"),
  [ROUTES.notificationSettings]: pageLoader("../pages/NotificationPreferencesPage.js", "NotificationPreferencesPage"),
  [ROUTES.incidents]: pageLoader("../pages/IncidentsPage.js", "IncidentsPage"),
  [ROUTES.reports]: pageLoader("../pages/ReportsPage.js", "ReportsOverviewPage"),
  [ROUTES.reportPilots]: pageLoader("../pages/ReportsPage.js", "PilotProgressReportPage"),
  [ROUTES.reportActions]: pageLoader("../pages/ReportsPage.js", "ActionsReportPage"),
  [ROUTES.reportKpis]: pageLoader("../pages/ReportsPage.js", "KpiReportPage"),
  [ROUTES.reportIncidents]: pageLoader("../pages/ReportsPage.js", "IncidentReportPage"),
});

const STAGE_LOADERS = Object.freeze([
  pageLoader("../pages/StageOnePage.js", "StageOnePage"),
  pageLoader("../pages/StageTwoPage.js", "StageTwoPage"),
  pageLoader("../pages/StageThreePage.js", "StageThreePage"),
  pageLoader("../pages/StageFourPage.js", "StageFourPage"),
  pageLoader("../pages/StageFivePage.js", "StageFivePage"),
  pageLoader("../pages/StageSixPage.js", "StageSixPage"),
  pageLoader("../pages/StageSevenPage.js", "StageSevenPage"),
  pageLoader("../pages/StageEightPage.js", "StageEightPage"),
  pageLoader("../pages/StageNinePage.js", "StageNinePage"),
  pageLoader("../pages/StageTenPage.js", "StageTenPage"),
  pageLoader("../pages/StageElevenPage.js", "StageElevenPage"),
  pageLoader("../pages/StageTwelvePage.js", "StageTwelvePage"),
  pageLoader("../pages/StageThirteenPage.js", "StageThirteenPage"),
  pageLoader("../pages/StageFourteenPage.js", "StageFourteenPage"),
  pageLoader("../pages/StageFifteenPage.js", "StageFifteenPage"),
  pageLoader("../pages/StageSixteenPage.js", "StageSixteenPage"),
  pageLoader("../pages/StageSeventeenPage.js", "StageSeventeenPage"),
  pageLoader("../pages/StageEighteenPage.js", "StageEighteenPage"),
  pageLoader("../pages/StageNineteenPage.js", "StageNineteenPage"),
]);

const getCurrentRoute = () => window.location.hash || ROUTES.dashboard;

const resolveRoute = async (currentRoute) => {
  const user = sessionStore.getCurrentUser();
  const permissions = user?.permissions ?? [];
  const roles = user?.roles ?? [];
  if (!canAccessRoute(currentRoute, permissions, roles)) {
    return { page: accessDeniedPage(currentRoute, permissions, roles), navigationRoute: "" };
  }
  const routePath = normalizeRoutePath(currentRoute);
  const exactPageLoader = ROUTE_LOADERS[routePath];

  if (exactPageLoader) {
    return {
      page: await exactPageLoader(),
      navigationRoute: routePath.startsWith("#/reports") ? ROUTES.reports : routePath,
    };
  }

  const reportPilotMatch = routePath.match(/^#\/reports\/pilots\/([^/?#]+)$/);
  if (reportPilotMatch) {
    return {
      page: await pageLoader("../pages/ReportsPage.js", "PilotOnePageReportPage")({ pilotId: reportPilotMatch[1] }),
      navigationRoute: ROUTES.reports,
    };
  }

  const pilotDetailsMatch = routePath.match(/^#\/pilots\/([^/]+)$/);
  const incidentCreateMatch = routePath.match(/^#\/pilots\/([^/]+)\/incidents\/new$/);
  const incidentDetailMatch = routePath.match(/^#\/incidents\/([^/?#]+)$/);
  const notificationDetailsMatch = routePath.match(/^#\/notifications\/([^/?#]+)$/);
  const stageMatch = matchStageRoute(routePath);

  if (incidentCreateMatch) {
    return {
      page: await pageLoader("../pages/IncidentCreatePage.js", "IncidentCreatePage")({ pilotId: incidentCreateMatch[1] }),
      navigationRoute: ROUTES.incidents,
    };
  }

  if (incidentDetailMatch) {
    return {
      page: await pageLoader("../pages/IncidentDetailPage.js", "IncidentDetailPage")({ incidentId: incidentDetailMatch[1] }),
      navigationRoute: ROUTES.incidents,
    };
  }

  if (notificationDetailsMatch) {
    return {
      page: await pageLoader("../pages/NotificationsPage.js", "NotificationsPage")({ notificationId: decodeURIComponent(notificationDetailsMatch[1]) }),
      navigationRoute: ROUTES.notifications,
    };
  }

  if (stageMatch) {
    return {
      page: await STAGE_LOADERS[stageMatch.stageNumber - 1]({ pilotId: stageMatch.pilotId }),
      navigationRoute: ROUTES.pilots,
    };
  }

  if (pilotDetailsMatch) {
    return {
      page: await pageLoader("../pages/PilotDetailsPage.js", "PilotDetailsPage")({ pilotId: pilotDetailsMatch[1] }),
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
let renderVersion = 0;

const renderRoute = async (appRoot) => {
  const version = ++renderVersion;
  cleanupStageNavigationGuard();
  cleanupStageActionLayout();
  cleanupAppShell();
  const currentRoute = getCurrentRoute();
  const loading = document.createElement("main");
  loading.className = "page loading-state";
  loading.textContent = "در حال بارگذاری صفحه…";
  appRoot.replaceChildren(loading);
  const resolvedRoute = await resolveRoute(currentRoute);
  if (version !== renderVersion) return;
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

  renderRoute(appRoot).catch(() => window.dispatchEvent(new Event("error")));
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
    await renderRoute(appRoot);
  };
  const handleBeforeUnload = (event) => {
    if (!hasNavigationGuard()) return;

    event.preventDefault();
    event.returnValue = "";
  };
  window.addEventListener("hashchange", handleHashChange);
  window.addEventListener("beforeunload", handleBeforeUnload);
  return () => {
    renderVersion += 1;
    window.removeEventListener("hashchange", handleHashChange);
    window.removeEventListener("beforeunload", handleBeforeUnload);
    cleanupStageNavigationGuard();
    cleanupStageActionLayout();
    cleanupAppShell();
    cleanupAppShell = () => {};
    clearNavigationGuard();
  };
};
