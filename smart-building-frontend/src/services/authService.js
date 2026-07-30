import { sessionStore } from "../app/sessionStore.js";
import { request } from "./httpClient.js";

export const authService = Object.freeze({
  requestOtp: (mobile) =>
    request("/auth/otp/request", {
      method: "POST",
      body: JSON.stringify({ mobile }),
    }),
  verifyOtp: async ({ requestId, code }) => {
    const response = await request("/auth/otp/verify", {
      method: "POST",
      body: JSON.stringify({ request_id: requestId, code }),
    });

    sessionStore.setSession({
      accessToken: response.access_token,
      user: response.user,
    });

    return response;
  },
  getCurrentUser: () => request("/auth/me"),
  logout: async () => {
    try {
      await request("/auth/logout", { method: "POST" });
    } finally {
      sessionStore.clear();
    }
  },
});

