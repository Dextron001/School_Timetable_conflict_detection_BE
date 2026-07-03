import { Navigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

// Guards a route. If `role` is given, only that role may enter; others are
// redirected to their own dashboard.
export default function ProtectedRoute({ role, children }) {
  const { user, loading } = useAuth();

  if (loading) {
    return (
      <div className="min-h-full grid place-items-center">
        <div className="h-8 w-8 rounded-full border-2 border-brand border-t-transparent animate-spin" />
      </div>
    );
  }

  if (!user) return <Navigate to="/login" replace />;

  if (role && user.role !== role) {
    return <Navigate to={user.role === "admin" ? "/admin" : "/client"} replace />;
  }

  return children;
}
