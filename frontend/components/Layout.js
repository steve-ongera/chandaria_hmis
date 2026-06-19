import { useEffect, useState } from "react";
import { useRouter } from "next/router";
import Navbar from "./Navbar";
import Sidebar from "./Sidebar";
import { isAuthenticated, getCurrentUser } from "../lib/api";

export default function Layout({ children }) {
  const router = useRouter();
  const [user, setUser] = useState({ role: null, username: null });
  const [checked, setChecked] = useState(false);

  useEffect(() => {
    if (!isAuthenticated()) {
      router.replace("/login");
      return;
    }
    setUser(getCurrentUser());
    setChecked(true);
  }, [router]);

  if (!checked) return null;

  return (
    <div className="app-shell">
      <Sidebar role={user.role} />
      <div className="main-content">
        <Navbar username={user.username} role={user.role} />
        <div className="page-container">{children}</div>
      </div>
    </div>
  );
}
