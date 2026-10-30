import axios from "axios";

const api = axios.create({ baseURL: "/api" });

export const getTokens = () => JSON.parse(localStorage.getItem("tokens") || "null");
export const setTokens = (t) =>
  t ? localStorage.setItem("tokens", JSON.stringify(t)) : localStorage.removeItem("tokens");

api.interceptors.request.use((cfg) => {
  const t = getTokens();
  if (t?.access) cfg.headers.Authorization = `Bearer ${t.access}`;
  return cfg;
});

// Renova o access token (uma única vez, mesmo com várias requisições falhando juntas).
let refreshing = null;
const NO_REFRESH = ["/auth/login/", "/auth/token/refresh/"];

api.interceptors.response.use(
  (r) => r,
  async (err) => {
    const { config, response } = err;
    const t = getTokens();
    if (response?.status === 401 && t?.refresh && !config._retry && !NO_REFRESH.some((p) => config.url.includes(p))) {
      config._retry = true;
      try {
        refreshing =
          refreshing ||
          axios.post("/api/auth/token/refresh/", { refresh: t.refresh }).finally(() => (refreshing = null));
        const { data } = await refreshing;
        setTokens({ access: data.access, refresh: data.refresh || t.refresh });
        config.headers.Authorization = `Bearer ${data.access}`;
        return api(config);
      } catch {
        setTokens(null);
        window.location.href = "/login";
      }
    }
    return Promise.reject(err);
  }
);

export const unwrap = (r) => r.data.results ?? r.data;

export function errorMessage(err) {
  const d = err.response?.data;
  if (!d) return "Não foi possível falar com o servidor.";
  if (typeof d === "string") return "Erro no servidor. Tente novamente.";
  if (d.detail) return d.detail;
  return Object.entries(d)
    .map(([k, v]) => `${k}: ${[].concat(v).join(" ")}`)
    .join(" | ");
}

export default api;
