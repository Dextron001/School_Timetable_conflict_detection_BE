import { Link } from "react-router-dom";

export default function NotFound() {
  return (
    <div className="min-h-full grid place-items-center px-4">
      <div className="text-center">
        <p className="text-7xl font-bold text-brand/30">404</p>
        <h1 className="mt-4 text-2xl font-bold">Page not found</h1>
        <p className="mt-2 text-sm text-muted">
          The page you're looking for doesn't exist or has been moved.
        </p>
        <Link to="/" className="btn-primary mt-6 inline-block">
          Back to dashboard
        </Link>
      </div>
    </div>
  );
}