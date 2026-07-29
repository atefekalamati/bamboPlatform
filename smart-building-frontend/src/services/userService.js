import { APP_CONFIG } from "../config/appConfig.js";
import { userMockService } from "../mock/userMockService.js";
import { request } from "./httpClient.js";

const userApiService = Object.freeze({
  getUsers: ({ search = "", page = 1, pageSize = 20 } = {}) => {
    const query = new URLSearchParams({ search, page, pageSize });

    return request(`/users?${query.toString()}`);
  },
  createUser: (userData) =>
    request("/users", {
      method: "POST",
      body: JSON.stringify(userData),
    }),
  updateUser: () =>
    Promise.reject(
      new Error("قرارداد API ویرایش کاربر هنوز توسط Backend تعریف نشده است."),
    ),
});

export const userService = APP_CONFIG.useMockApi
  ? userMockService
  : userApiService;
