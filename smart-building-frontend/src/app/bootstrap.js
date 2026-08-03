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

const APP_ROOT_ID = "app";

startPersianDigitLocalization();
startPersianDatePickers();

const renderAuthenticatedApp = (appRoot) => {
  appRoot.replaceChildren();
  startRouter(appRoot);
};

const renderLogin = (appRoot) => {
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

bootstrap();

