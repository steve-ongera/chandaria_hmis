import { useRouter } from "next/router";
import { logout } from "../lib/api";

export default function Navbar({ username, role }) {
  const router = useRouter();

  const handleLogout = () => {
    logout();
    router.push("/login");
  };

  return (
    <header className="navbar">
      <div className="navbar-brand">
        <i className="bi bi-clipboard2-pulse" />
        <span>Hospital Management System</span>
      </div>
      <div className="navbar-user">
        <i className="bi bi-person-circle" />
        <span>{username} <span className="text-muted">· {role === "DOCTOR" ? "Doctor" : "Nurse"}</span></span>
        <button className="navbar-logout" onClick={handleLogout}>
          <i className="bi bi-box-arrow-right" />
          Logout
        </button>
      </div>
    </header>
  );
}
