import { AuthLayout } from "../layouts/AuthLayout.js";
import { LoginPage } from "../pages/LoginPage.js";
import { authService } from "../services/authService.js";
import { sessionStore } from "./sessionStore.js";
import { startRouter } from "./router.js";

const APP_ROOT_ID = "app";

const renderAuthenticatedApp = (appRoot) => {
  appRoot.replaceChildren();
  startRouter(appRoot);
};

const renderLogin = (appRoot) => {
  appRoot.replaceChildren(
    AuthLayout({
      content: LoginPage({
        onAuthenticated: () => renderAuthenticatedApp(appRoot),
      }),
    }),
  );
};

const bootstrap = async () => {
  const appRoot = document.getElementById(APP_ROOT_ID);

  if (!appRoot) return;

  if (!sessionStore.getToken()) {
    renderLogin(appRoot);
    return;
  }

  try {
    const currentUser = await authService.getCurrentUser();
    sessionStore.setCurrentUser(currentUser);
    renderAuthenticatedApp(appRoot);
  } catch {
    sessionStore.clear();
    renderLogin(appRoot);
  }
};

bootstrap();

