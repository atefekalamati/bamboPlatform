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
  themeStore.init(sessionStore.getCurrentUser()?.id);
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

const renderSessionRecovery = (appRoot, retry) => {
  stopRouter();
  stopRouter = () => {};
  notificationStore.stop();
  const state = document.createElement("main");
  const message = document.createElement("p");
  const retryButton = document.createElement("button");
  state.className = "fatal-error";
  message.textContent = "ارتباط با سرور موقتاً برقرار نشد. نشست شما حفظ شده است.";
  retryButton.className = "button button--primary";
  retryButton.type = "button";
  retryButton.textContent = "تلاش مجدد";
  retryButton.addEventListener("click", retry);
  state.append(message, retryButton);
  appRoot.replaceChildren(state);
};

const bootstrap = async () => {
  const appRoot = document.getElementById(APP_ROOT_ID);

  if (!appRoot) return;

  registerGlobalErrorHandling(appRoot);

  if (!sessionStore.hasSession()) {
    renderLogin(appRoot);
    return;
  }

  try {
    const currentUser = await authService.getCurrentUser();
    sessionStore.setCurrentUser(currentUser);
    const preferences = await preferenceService.getPreferences().catch(() => null);
    themeStore.syncFromServer(preferences?.theme, currentUser.id);
    renderAuthenticatedApp(appRoot);
  } catch (error) {
    if (!sessionStore.hasSession() || error?.status === 401) {
      renderLogin(appRoot);
      return;
    }
    renderSessionRecovery(appRoot, bootstrap);
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

