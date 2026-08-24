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
      refreshToken: response.refresh_token,
      expiresIn: response.expires_in,
      refreshExpiresIn: response.refresh_expires_in,
      user: response.user,
    });

    return response;
  },
  getCurrentUser: () => request("/auth/me"),
  updateMyName: async (displayName) => {
    const user = await request("/auth/me", {
      method: "PATCH",
      body: JSON.stringify({ display_name: displayName }),
    });
    sessionStore.setCurrentUser(user);
    return user;
  },
  logout: async () => {
    const refreshToken = sessionStore.getRefreshToken();
    try {
      await request("/auth/logout", {
        method: "POST",
        body: refreshToken
          ? JSON.stringify({ refresh_token: refreshToken })
          : undefined,
      });
    } finally {
      sessionStore.clear();
    }
  },
});

