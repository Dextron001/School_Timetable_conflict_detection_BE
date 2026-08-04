// Centralised API client. All calls attach the JWT from localStorage.
// Scope is FACULTY-level (FPAS or FSMS), not individual departments.
const BASE_URL = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";

function getToken() {
  return localStorage.getItem("token");
}

function clearAuth() {
  localStorage.removeItem("token");
  if (!window.location.pathname.includes("/login")) {
    window.location.href = "/login";
  }
}

function buildQuery(params) {
  const parts = [];
  for (const [key, val] of Object.entries(params)) {
    if (val !== undefined && val !== null && val !== "") {
      parts.push(`${key}=${encodeURIComponent(val)}`);
    }
  }
  return parts.length ? `?${parts.join("&")}` : "";
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

  if (raw) return res;
  if (res.status === 204) return null;
  return res.json();
}

export const api = {
  login: (username, password) =>
    request("/auth/login", { method: "POST", body: { username, password }, auth: false }),
  me: () => request("/auth/me"),
  faculties: () => request("/faculties"),

  courses: (faculty) =>
    request(`/courses${buildQuery({ faculty })}`),
  createCourse: (payload) =>
    request("/courses", { method: "POST", body: payload }),
  updateCourse: (id, payload) =>
    request(`/courses/${id}`, { method: "PATCH", body: payload }),
  deleteCourse: (id) =>
    request(`/courses/${id}`, { method: "DELETE" }),

  // Conflicts now returns both IDs and detailed causes
  conflicts: (faculty) =>
    request(`/conflicts${buildQuery({ faculty })}`),
  generate: (faculty) =>
    request(`/generate${buildQuery({ faculty })}`, { method: "PUT" }),
  resolve: (faculty) =>
    request(`/resolve${buildQuery({ faculty })}`, { method: "PUT" }),

  exportPdf: (faculty) =>
    request(`/export-pdf${buildQuery({ faculty })}`, { raw: true }),

  users: () => request("/users"),
  createUser: (payload) =>
    request("/users", { method: "POST", body: payload }),
  updateUser: (id, payload) =>
    request(`/users/${id}`, { method: "PATCH", body: payload }),
  deleteUser: (id) =>
    request(`/users/${id}`, { method: "DELETE" }),

  // ── Complaints ──
  submitComplaint: (payload) =>
    request("/complaints", { method: "POST", body: payload }),
  complaints: (faculty, status) =>
    request(`/complaints${buildQuery({ faculty, status })}`),
  resolveComplaint: (id, payload) =>
    request(`/complaints/${id}`, { method: "PATCH", body: payload }),
  myComplaints: () => request("/complaints/my"),

  // ── Complaint Messages ──
  getMessages: (complaintId) =>
    request(`/complaints/${complaintId}/messages`),
  sendMessage: (complaintId, message) =>
    request(`/complaints/${complaintId}/messages`, { method: "POST", body: { message } }),

  // ── Notifications ──
  notifications: () => request("/notifications"),
};

export { BASE_URL };