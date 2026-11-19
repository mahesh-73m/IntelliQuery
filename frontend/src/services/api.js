import axios from "axios";

export const TOKEN_KEY = "iq_token";
const api = axios.create({ baseURL: import.meta.env.VITE_API_URL || "/api", timeout: 130000 });

api.interceptors.request.use((cfg) => {
  const t = localStorage.getItem(TOKEN_KEY);
  if (t) cfg.headers.Authorization = `Bearer ${t}`;
  return cfg;
});

api.interceptors.response.use(
  (r) => r,
  (err) => {
    const url = err.config?.url || "";
    if (err.response?.status === 401 && !url.startsWith("/auth/login") && !url.startsWith("/auth/register")) {
      localStorage.removeItem(TOKEN_KEY);
      if (location.pathname !== "/login") location.assign("/login");
    }
    return Promise.reject(err);
  }
);

export const errMsg = (e) => {
  if (e.code === "ECONNABORTED") return "The request timed out. Try again.";
  if (!e.response) return "Cannot reach the server. Is the backend running?";
  const d = e.response.data?.detail;
  return typeof d === "string" ? d : "Something went wrong.";
};

export const auth = {
  login: (b) => api.post("/auth/login", b).then((r) => r.data),
  register: (b) => api.post("/auth/register", b).then((r) => r.data),
  me: () => api.get("/auth/me").then((r) => r.data),
  settings: () => api.get("/auth/settings").then((r) => r.data),
  updateSettings: (b) => api.put("/auth/settings", b).then((r) => r.data),
};
export const conversations = {
  list: () => api.get("/conversations").then((r) => r.data),
  create: (title) => api.post("/conversations", { title }).then((r) => r.data),
  get: (id) => api.get(`/conversations/${id}`).then((r) => r.data),
  remove: (id) => api.delete(`/conversations/${id}`),
  send: (id, content) => api.post(`/conversations/${id}/messages`, { content }).then((r) => r.data),
  clarify: (id, option_id) => api.post(`/conversations/${id}/clarifications`, { option_id }).then((r) => r.data),
};
export const queries = {
  execute: (b) => api.post("/query/execute", b).then((r) => r.data),
  history: (params) => api.get("/query/history", { params }).then((r) => r.data),
  saved: () => api.get("/query/saved").then((r) => r.data),
  save: (b) => api.post("/query/saved", b).then((r) => r.data),
  removeSaved: (id) => api.delete(`/query/saved/${id}`),
};
export const database = {
  status: () => api.get("/database/status").then((r) => r.data),
  schema: () => api.get("/database/schema").then((r) => r.data),
};
export const analytics = {
  overview: () => api.get("/analytics/overview").then((r) => r.data),
  evaluation: () => api.get("/analytics/evaluation").then((r) => r.data),
};
export default api;
