import { useEffect, useState } from "react";
import { api } from "../api";

const LEVELS = ["100", "200", "300", "400"];

export default function ScopeSelector({ dept, level, onChange }) {
  const [departments, setDepartments] = useState([]);

  useEffect(() => {
    api.departments().then(setDepartments).catch(() => setDepartments([]));
  }, []);

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
      <div>
        <label className="label">Department</label>
        <select
          className="input"
          value={dept}
          onChange={(e) => onChange({ dept: e.target.value, level })}
        >
          <option value="">Select department</option>
          {departments.map((d) => (
            <option key={d.code} value={d.code}>
              {d.name} ({d.code})
            </option>
          ))}
        </select>
      </div>
      <div>
        <label className="label">Academic Level</label>
        <select
          className="input"
          value={level}
          onChange={(e) => onChange({ dept, level: e.target.value })}
        >
          <option value="">Select level</option>
          {LEVELS.map((l) => (
            <option key={l} value={l}>
              {l} Level
            </option>
          ))}
        </select>
      </div>
    </div>
  );
}
