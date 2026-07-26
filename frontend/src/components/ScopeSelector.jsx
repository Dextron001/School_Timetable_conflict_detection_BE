import { useEffect, useState } from "react";
import { api } from "../api";

export default function ScopeSelector({ faculty, onChange }) {
  const [faculties, setFaculties] = useState([]);

  useEffect(() => {
    api.faculties().then(setFaculties).catch(() => setFaculties([]));
  }, []);

  return (
    <div>
      <label className="label">Faculty</label>
      <select
        className="input"
        value={faculty}
        onChange={(e) => onChange(e.target.value)}
      >
        <option value="">Select faculty</option>
        {faculties.map((f) => (
          <option key={f.code} value={f.code}>
            {f.name} ({f.code})
          </option>
        ))}
      </select>
    </div>
  );
}