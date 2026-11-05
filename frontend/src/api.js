export const API_BASE = (import.meta.env.VITE_API_URL || "http://localhost:8000").replace(/\/$/, "");

export class ApiError extends Error {
  constructor(message, status) {
    super(message);
    this.status = status;
  }
}

export const getToken = () => localStorage.getItem("token");
export const clearSession = () => {
  localStorage.removeItem("token");
  localStorage.removeItem("user");
};

function messageFrom(data, status) {
  const d = data && data.detail;
  if (typeof d === "string") return d;
  if (Array.isArray(d)) {
    return d.map((e) => `${(e.loc || []).slice(1).join(".")}: ${e.msg}`).join(" · ");
  }
  return `Error ${status}`;
}

/** Llamada a la API. `body` = JSON, `form` = formulario (solo el login), `params` = query string. */
export async function api(path, { method = "GET", body, form, params } = {}) {
  const headers = {};
  const token = getToken();
  if (token) headers.Authorization = `Bearer ${token}`;

  let payload;
  if (form) {
    headers["Content-Type"] = "application/x-www-form-urlencoded";
    payload = new URLSearchParams(form);
  } else if (body !== undefined) {
    headers["Content-Type"] = "application/json";
    payload = JSON.stringify(body);
  }

  let url = API_BASE + path;
  if (params) {
    const qs = new URLSearchParams();
    Object.entries(params).forEach(([k, v]) => {
      if (v !== "" && v != null) qs.append(k, v);
    });
    const s = qs.toString();
    if (s) url += "?" + s;
  }

  let res;
  try {
    res = await fetch(url, { method, headers, body: payload });
  } catch {
    throw new ApiError("No se pudo conectar con el servidor. ¿Está encendida la API?", 0);
  }

  if (res.status === 401 && token && !path.startsWith("/auth/login")) {
    clearSession();
    window.dispatchEvent(new Event("auth:expired"));
  }
  if (res.status === 204) return null;

  const data = await res.json().catch(() => null);
  if (!res.ok) throw new ApiError(messageFrom(data, res.status), res.status);
  return data;
}