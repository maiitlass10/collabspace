import { apiRequest } from "./api.js";

export const documentsApi = {
  list: ({ search = "", page = 1 } = {}) => {
    const params = new URLSearchParams({ page: String(page) });
    if (search.trim()) params.set("search", search.trim());
    return apiRequest(`/api/documents/?${params}`);
  },
  get: (id) => apiRequest(`/api/documents/${encodeURIComponent(id)}/`),
  create: (title) => apiRequest("/api/documents/", { method: "POST", body: { title } }),
  rename: (id, title) =>
    apiRequest(`/api/documents/${encodeURIComponent(id)}/`, { method: "PATCH", body: { title } }),
  remove: (id) => apiRequest(`/api/documents/${encodeURIComponent(id)}/`, { method: "DELETE" }),
};

export const TITLE_MAX_LENGTH = 200;
