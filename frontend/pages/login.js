import { useState } from "react";
import { useRouter } from "next/router";
import { login } from "../lib/api";

export default function LoginPage() {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [role, setRole] = useState("NURSE");
  const [error, setError] = useState("");
  const router = useRouter();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    try {
      await login(username, password, role);
      router.push(role === "DOCTOR" ? "/queue" : "/reception");
    } catch (err) {
      setError("Invalid username or password.");
    }
  };

  return (
    <div className="login-wrapper">
      <div className="login-card">
        <h2><i className="bi bi-hospital" /> HMS Login</h2>
        <form onSubmit={handleSubmit}>
          <label>Username</label>
          <input
            className="form-control"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
          />

          <label>Password</label>
          <input
            type="password"
            className="form-control"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />

          <label>Login as</label>
          <select className="form-control" value={role} onChange={(e) => setRole(e.target.value)}>
            <option value="NURSE">Nurse / Reception</option>
            <option value="DOCTOR">Doctor</option>
          </select>

          {error && <p className="text-danger">{error}</p>}

          <button type="submit" className="btn" style={{ width: "100%", justifyContent: "center" }}>
            <i className="bi bi-box-arrow-in-right" /> Login
          </button>
        </form>
      </div>
    </div>
  );
}
