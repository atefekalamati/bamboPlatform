import { APP_CONFIG } from "../config/appConfig.js";
import { pilotMockService } from "../mock/pilotMockService.js";
import { request } from "./httpClient.js";

const pilotApiService = Object.freeze({
  getPilots: ({ search = "", status = "", page = 1, pageSize = 20 } = {}) => {
    const query = new URLSearchParams({ search, status, page, pageSize });

    return request(`/pilots?${query.toString()}`);
  },
  getPilotById: (pilotId) => request(`/pilots/${pilotId}`),
});

export const pilotService = APP_CONFIG.useMockApi
  ? pilotMockService
  : pilotApiService;
