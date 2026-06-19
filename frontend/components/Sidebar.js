import Link from "next/link";
import { useRouter } from "next/router";

const NURSE_LINKS = [
  { href: "/reception", label: "Reception", icon: "bi-person-plus" },
  { href: "/triage", label: "Triage", icon: "bi-heart-pulse" },
  { href: "/billing", label: "Billing & Dispensing", icon: "bi-receipt" },
  { href: "/walkin", label: "Walk-in Sale", icon: "bi-bag-check" },
];

const DOCTOR_LINKS = [
  { href: "/queue", label: "Consultation Queue", icon: "bi-people" },
];

export default function Sidebar({ role }) {
  const router = useRouter();
  const links = role === "DOCTOR" ? DOCTOR_LINKS : NURSE_LINKS;

  return (
    <aside className="sidebar">
      <div className="sidebar-brand">
        <i className="bi bi-hospital" />
        <span>HMS</span>
      </div>
      <div className="sidebar-role">{role === "DOCTOR" ? "Doctor menu" : "Nurse menu"}</div>
      <nav className="sidebar-nav">
        {links.map((link) => {
          const active = router.pathname === link.href || router.pathname.startsWith(link.href + "/");
          return (
            <Link key={link.href} href={link.href} className={`sidebar-link ${active ? "active" : ""}`}>
              <i className={`bi ${link.icon}`} />
              <span>{link.label}</span>
            </Link>
          );
        })}
      </nav>
    </aside>
  );
}
