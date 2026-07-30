const TOKEN_KEY = "bambo_access_token";
let currentUser = null;

export const sessionStore = Object.freeze({
  getToken: () => window.sessionStorage.getItem(TOKEN_KEY),
  setSession: ({ accessToken, user }) => {
    window.sessionStorage.setItem(TOKEN_KEY, accessToken);
    currentUser = user;
  },
  setCurrentUser: (user) => {
    currentUser = user;
  },
  getCurrentUser: () => currentUser,
  clear: () => {
    window.sessionStorage.removeItem(TOKEN_KEY);
    currentUser = null;
  },
});

