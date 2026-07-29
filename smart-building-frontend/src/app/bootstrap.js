import { startRouter } from "./router.js";

const APP_ROOT_ID = "app";

const bootstrap = () => {
  const appRoot = document.getElementById(APP_ROOT_ID);

  if (!appRoot) return;

  startRouter(appRoot);
};

bootstrap();

