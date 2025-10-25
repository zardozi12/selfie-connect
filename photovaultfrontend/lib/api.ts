import axios, { AxiosError, InternalAxiosRequestConfig } from "axios";

export const api = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000",
  withCredentials: true,
});

api.interceptors.request.use((cfg: InternalAxiosRequestConfig) => {
  const t = localStorage.getItem("access_token");
  const csrf = localStorage.getItem("csrf_token");

  // Support both AxiosHeaders and plain object headers
  const setHeader = (key: string, value: string) => {
    const h = cfg.headers as any;
    if (h?.set && typeof h.set === "function") {
      h.set(key, value);
    } else {
      cfg.headers = { ...(cfg.headers || {}), [key]: value } as any;
    }
  };

  if (t) setHeader("Authorization", `Bearer ${t}`);
  if (csrf) setHeader("X-CSRF-Token", csrf);

  return cfg;
});

let refreshing = false;

api.interceptors.response.use(undefined, async (err: AxiosError) => {
  if (err.response?.status === 401 && !refreshing) {
    refreshing = true;
    try {
      const { data } = await axios.post(
        `${api.defaults.baseURL}/auth/refresh`,
        {},
        { withCredentials: true }
      );
      localStorage.setItem("access_token", data.access_token);
      refreshing = false;

      // Retry original request with new token
      const cfg = err.config!;
      const h = (cfg.headers || {}) as any;
      if (h?.set && typeof h.set === "function") {
        h.set("Authorization", `Bearer ${data.access_token}`);
      } else {
        cfg.headers = { ...(cfg.headers || {}), Authorization: `Bearer ${data.access_token}` } as any;
      }
      return api.request(cfg);
    } catch {
      refreshing = false;
    }
  }
  throw err;
});