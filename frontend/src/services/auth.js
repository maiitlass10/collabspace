import { apiRequest } from "./api.js";

export const authApi = {
  /** Returns {authenticated, user} and makes sure the CSRF cookie exists. */
  session: () => apiRequest("/api/auth/session/"),
  login: (email, password) =>
    apiRequest("/api/auth/login/", { method: "POST", body: { email, password } }),
  register: (data) => apiRequest("/api/auth/register/", { method: "POST", body: data }),
  logout: () => apiRequest("/api/auth/logout/", { method: "POST" }),
};
