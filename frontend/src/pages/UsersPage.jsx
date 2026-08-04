import { useEffect, useState } from "react";
import { api } from "../api";
import DashboardHeader from "../components/DashboardHeader";
import { useAuth } from "../context/AuthContext";
import { useToast } from "../context/ToastContext";

export default function UsersPage() {
  const toast = useToast();
  const { user: me } = useAuth();
  const [users, setUsers] = useState([]);
  const [busy, setBusy] = useState(false);
  const [adding, setAdding] = useState(false);
  const [form, setForm] = useState({ username: "", full_name: "", password: "", role: "client" });
  const [editingId, setEditingId] = useState(null);
  const [editForm, setEditForm] = useState({ full_name: "", password: "", role: "" });

  async function refresh() {
    try {
      setUsers(await api.users());
    } catch (e) {
      toast.error(e.message);
    }
  }

  useEffect(() => {
    refresh();
  }, []);

  async function handleAdd(e) {
    e.preventDefault();
    if (!form.username || !form.full_name || !form.password) {
      return toast.error("All fields are required.");
    }
    setBusy(true);
    try {
      await api.createUser(form);
      toast.success("User created.");
      setForm({ username: "", full_name: "", password: "", role: "client" });
      setAdding(false);
      await refresh();
    } catch (e) {
      toast.error(e.message);
    } finally {
      setBusy(false);
    }
  }

  function startEdit(u) {
    setEditingId(u.id);
    setEditForm({ full_name: u.full_name, password: "", role: u.role });
  }

  async function handleSaveEdit(id) {
    const payload = {};
    if (editForm.full_name) payload.full_name = editForm.full_name;
    if (editForm.password) payload.password = editForm.password;
    if (editForm.role) payload.role = editForm.role;
    try {
      await api.updateUser(id, payload);
      toast.success("User updated.");
      setEditingId(null);
      await refresh();
    } catch (e) {
      toast.error(e.message);
    }
  }

  async function handleDelete(id, username) {
    if (!confirm(`Delete user "${username}"? This cannot be undone.`)) return;
    try {
      await api.deleteUser(id);
      toast.success("User deleted.");
      await refresh();
    } catch (e) {
      toast.error(e.message);
    }
  }

  function displayRole(role) {
    return role === "admin" ? "Admin" : "Student";
  }

  return (
    <div className="min-h-full">
      <DashboardHeader title="User Management" subtitle="Create, edit and remove accounts" />

      <main className="max-w-4xl mx-auto px-6 py-8 space-y-6">
        <div className="card p-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-bold">Users</h2>
            <button
              className="btn-primary"
              onClick={() => setAdding(!adding)}
            >
              {adding ? "Cancel" : "+ Add user"}
            </button>
          </div>

          {adding && (
            <form onSubmit={handleAdd} className="border border-line rounded-xl p-5 space-y-4 mb-4 bg-surface">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label className="label">Username</label>
                  <input
                    className="input"
                    value={form.username}
                    onChange={(e) => setForm({ ...form, username: e.target.value })}
                    required
                  />
                </div>
                <div>
                  <label className="label">Full name</label>
                  <input
                    className="input"
                    value={form.full_name}
                    onChange={(e) => setForm({ ...form, full_name: e.target.value })}
                    required
                  />
                </div>
                <div>
                  <label className="label">Password</label>
                  <input
                    type="password"
                    className="input"
                    value={form.password}
                    onChange={(e) => setForm({ ...form, password: e.target.value })}
                    required
                  />
                </div>
                <div>
                  <label className="label">Role</label>
                  <select
                    className="input"
                    value={form.role}
                    onChange={(e) => setForm({ ...form, role: e.target.value })}
                  >
                    <option value="client">Student</option>
                    <option value="admin">Admin</option>
                  </select>
                </div>
              </div>
              <div className="flex justify-end">
                <button className="btn-primary" disabled={busy}>
                  {busy ? "Creating…" : "Create user"}
                </button>
              </div>
            </form>
          )}

          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead>
                <tr className="text-[11px] uppercase tracking-wide text-muted border-b border-line">
                  <th className="py-3 pr-4 font-semibold">Username</th>
                  <th className="py-3 pr-4 font-semibold">Full Name</th>
                  <th className="py-3 pr-4 font-semibold">Role</th>
                  <th className="py-3 pr-4 font-semibold text-right">Actions</th>
                </tr>
              </thead>
              <tbody>
                {users.map((u) => (
                  <tr key={u.id} className="border-b border-line hover:bg-surface transition">
                    {editingId === u.id ? (
                      <>
                        <td className="py-3 pr-4 font-mono">{u.username}</td>
                        <td className="py-3 pr-4">
                          <input
                            className="input !py-1.5"
                            value={editForm.full_name}
                            onChange={(e) => setEditForm({ ...editForm, full_name: e.target.value })}
                          />
                        </td>
                        <td className="py-3 pr-4">
                          <select
                            className="input !py-1.5"
                            value={editForm.role}
                            onChange={(e) => setEditForm({ ...editForm, role: e.target.value })}
                          >
                            <option value="client">Student</option>
                            <option value="admin">Admin</option>
                          </select>
                        </td>
                        <td className="py-3 pr-4 text-right space-x-2">
                          <button
                            className="text-brand font-semibold text-xs hover:underline"
                            onClick={() => handleSaveEdit(u.id)}
                          >
                            Save
                          </button>
                          <button
                            className="text-muted text-xs hover:underline"
                            onClick={() => setEditingId(null)}
                          >
                            Cancel
                          </button>
                        </td>
                      </>
                    ) : (
                      <>
                        <td className="py-3 pr-4 font-mono">{u.username}</td>
                        <td className="py-3 pr-4">{u.full_name}</td>
                        <td className="py-3 pr-4">
                          <span
                            className={`badge ${
                              u.role === "admin"
                                ? "bg-brand/15 text-brand"
                                : "bg-emerald-100 text-emerald-700 dark:bg-emerald-900 dark:text-emerald-300"
                            }`}
                          >
                            {displayRole(u.role)}
                          </span>
                        </td>
                        <td className="py-3 pr-4 text-right space-x-2">
                          <button
                            className="text-brand font-semibold text-xs hover:underline"
                            onClick={() => startEdit(u)}
                          >
                            Edit
                          </button>
                          {u.id !== me.id && (
                            <button
                              className="text-red-500 font-semibold text-xs hover:underline"
                              onClick={() => handleDelete(u.id, u.username)}
                            >
                              Delete
                            </button>
                          )}
                        </td>
                      </>
                    )}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {users.length === 0 && (
            <p className="text-center text-sm text-muted py-8">No users found.</p>
          )}
        </div>
      </main>
    </div>
  );
}