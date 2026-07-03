// Centralised API client. All calls attach the JWT from localStorage.
const BASE_URL = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";

function getToken() {
  return localStorage.getItem("token");
}

function clearAuth() {
  localStorage.removeItem("token");
  // Only redirect if we're not already on the login page
  if (!window.location.pathname.includes("/login")) {
    window.location.href = "/login";
  }
}

async function request(path, { method = "GET", body, auth = true, raw = false } = {}) {
  const headers = {};
  if (body) headers["Content-Type"] = "application/json";
  if (auth && getToken()) headers["Authorization"] = `Bearer ${getToken()}`;

  const res = await fetch(`${BASE_URL}${path}`, {
    method,
    headers,
    body: body ? JSON.stringify(body) : undefined,
  });

  // Auto-logout on expired/invalid token
  if (res.status === 401 && auth) {
    clearAuth();
    throw new Error("Session expired — please log in again.");
  }

  if (!res.ok) {
    let detail = `Request failed (${res.status})`;
    try {
      const data = await res.json();
      detail = data.detail || detail;
    } catch {
      /* ignore */
    }
    throw new Error(detail);
  }

  if (raw) return res; // caller wants the raw Response (e.g. for blobs)
  if (res.status === 204) return null;
  return res.json();
}

export const api = {
  login: (username, password) =>
    request("/auth/login", { method: "POST", body: { username, password }, auth: false }),
  me: () => request("/auth/me"),
  departments: () => request("/departments"),

  // Courses
  courses: (dept, level) =>
    request(`/courses?department=${encodeURIComponent(dept)}&academic_level=${encodeURIComponent(level)}`),
  createCourse: (payload) =>
    request("/courses", { method: "POST", body: payload }),
  updateCourse: (id, payload) =>
    request(`/courses/${id}`, { method: "PATCH", body: payload }),
  deleteCourse: (id) =>
    request(`/courses/${id}`, { method: "DELETE" }),

  // Timetable actions
  conflicts: (dept, level) =>
    request(`/conflicts?department=${encodeURIComponent(dept)}&academic_level=${encodeURIComponent(level)}`),
  generate: (dept, level) =>
    request(`/generate?department=${encodeURIComponent(dept)}&academic_level=${encodeURIComponent(level)}`, { method: "PUT" }),
  resolve: (dept, level) =>
    request(`/resolve?department=${encodeURIComponent(dept)}&academic_level=${encodeURIComponent(level)}`, { method: "PUT" }),

  // Export
  exportPdf: (dept, level) =>
    request(`/export-pdf?department=${encodeURIComponent(dept)}&academic_level=${encodeURIComponent(level)}`, { raw: true }),

  // Users
  users: () => request("/users"),
  createUser: (payload) =>
    request("/users", { method: "POST", body: payload }),
  updateUser: (id, payload) =>
    request(`/users/${id}`, { method: "PATCH", body: payload }),
  deleteUser: (id) =>
    request(`/users/${id}`, { method: "DELETE" }),
};

export { BASE_URL };