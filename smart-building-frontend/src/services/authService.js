import { APP_CONFIG } from "../config/appConfig.js";
import { authMockService } from "../mock/authMockService.js";
import { request } from "./httpClient.js";

const authApiService = Object.freeze({
  requestOtp: (phoneNumber) =>
    request("/auth/otp/request", {
      method: "POST",
      body: JSON.stringify({ phoneNumber }),
    }),
  verifyOtp: ({ phoneNumber, otpCode }) =>
    request("/auth/otp/verify", {
      method: "POST",
      body: JSON.stringify({ phoneNumber, otpCode }),
    }),
});

export const authService = APP_CONFIG.useMockApi
  ? authMockService
  : authApiService;

