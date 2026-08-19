import { AuthLayout } from "../layouts/AuthLayout.js";
import { LoginPage } from "../pages/LoginPage.js";
import { authService } from "../services/authService.js";
import { preferenceService } from "../services/preferenceService.js";
import { startPersianDigitLocalization } from "../utils/persianDigits.js";
import { startPersianDatePickers } from "../components/PersianDatePicker.js";
import {
  markApiErrorFields,
  onApiError,
  onAuthenticationRequired,
} from "./apiErrorPresenter.js";
import { sessionStore } from "./sessionStore.js";
import { startRouter } from "./router.js";
import { themeStore } from "./themeStore.js";
import { notificationStore } from "./notificationStore.js";
import { startConnectionStatus } from "../components/ConnectionStatus.js";
import { startLiveRegionEnhancements } from "./accessibility.js";

const APP_ROOT_ID = "app";

startPersianDigitLocalization();
startPersianDatePickers();
startConnectionStatus();
startLiveRegionEnhancements();

let stopRouter = () => {};

const renderAuthenticatedApp = (appRoot) => {
  stopRouter();
  appRoot.replaceChildren();
  stopRouter = startRouter(appRoot);
};

const renderLogin = (appRoot) => {
  stopRouter();
  stopRouter = () => {};
  notificationStore.stop();
  appRoot.replaceChildren(
    AuthLayout({
      content: LoginPage({
        onAuthenticated: () => renderAuthenticatedApp(appRoot),
      }),
    }),
  );
};

const registerGlobalErrorHandling = (appRoot) => {
  onApiError(({ detail: error }) => markApiErrorFields(appRoot, error));
  onAuthenticationRequired(() => renderLogin(appRoot));
};

const bootstrap = async () => {
  const appRoot = document.getElementById(APP_ROOT_ID);

  if (!appRoot) return;

  registerGlobalErrorHandling(appRoot);

  if (!sessionStore.getToken()) {
    renderLogin(appRoot);
    return;
  }

  try {
    const currentUser = await authService.getCurrentUser();
    sessionStore.setCurrentUser(currentUser);
    const preferences = await preferenceService.getPreferences().catch(() => null);
    themeStore.syncFromServer(preferences?.theme);
    renderAuthenticatedApp(appRoot);
  } catch {
    sessionStore.clear();
    renderLogin(appRoot);
  }
};

const renderFatalError = () => {
  const appRoot = document.getElementById(APP_ROOT_ID);
  if (!appRoot) return;
  const container = document.createElement("main");
  const heading = document.createElement("h1");
  const message = document.createElement("p");
  const retry = document.createElement("button");
  container.className = "fatal-error";
  heading.textContent = "اجرای سامانه با مشکل روبه‌رو شد";
  message.textContent = "صفحه را دوباره بارگذاری کنید. اگر مشکل ادامه داشت با پشتیبانی تماس بگیرید.";
  retry.className = "button button--primary";
  retry.type = "button";
  retry.textContent = "بارگذاری مجدد";
  retry.addEventListener("click", () => window.location.reload());
  container.append(heading, message, retry);
  appRoot.replaceChildren(container);
};

window.addEventListener("error", () => renderFatalError());
window.addEventListener("unhandledrejection", (event) => {
  event.preventDefault();
  renderFatalError();
});

bootstrap().catch(() => renderFatalError());

