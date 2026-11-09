import { apiRequest } from "./api.js";

const docUrl = (id) => `/api/documents/${encodeURIComponent(id)}/`;

export const documentsApi = {
  /** scope: "owned" (my documents) | "shared" (shared with me) | "" (all) */
  list: ({ search = "", page = 1, scope = "" } = {}) => {
    const params = new URLSearchParams({ page: String(page) });
    if (search.trim()) params.set("search", search.trim());
    if (scope) params.set("scope", scope);
    return apiRequest(`/api/documents/?${params}`);
  },
  get: (id) => apiRequest(docUrl(id)),
  create: (title) => apiRequest("/api/documents/", { method: "POST", body: { title } }),
  rename: (id, title) => apiRequest(docUrl(id), { method: "PATCH", body: { title } }),
  remove: (id) => apiRequest(docUrl(id), { method: "DELETE" }),

  // --- sharing (owner only) ---
  members: (id) => apiRequest(`${docUrl(id)}members/`),
  share: (id, email, role) => apiRequest(`${docUrl(id)}members/`, { method: "POST", body: { email, role } }),
  changeRole: (id, memberId, role) =>
    apiRequest(`${docUrl(id)}members/${memberId}/`, { method: "PATCH", body: { role } }),
  removeMember: (id, memberId) => apiRequest(`${docUrl(id)}members/${memberId}/`, { method: "DELETE" }),
};

export const TITLE_MAX_LENGTH = 200;

export const ROLE_LABELS = {
  owner: "المالك",
  editor: "محرِّر",
  viewer: "قارئ",
};

export const canEdit = (role) => role === "owner" || role === "editor";
export const isOwner = (role) => role === "owner";
