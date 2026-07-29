import { APP_CONFIG } from "../config/appConfig.js";
import { roleMockService } from "../mock/roleMockService.js";
import { request } from "./httpClient.js";

const roleApiService = Object.freeze({
  getRoles: () => request("/roles"),
});

export const roleService = APP_CONFIG.useMockApi
  ? roleMockService
  : roleApiService;

