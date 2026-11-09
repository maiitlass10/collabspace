import { useEffect, useState } from "react";
import { NavLink, Outlet, useLocation, useNavigate } from "react-router";
import { useAuth } from "../context/AuthContext.jsx";
import Avatar from "../components/ui/Avatar.jsx";

const NAV_ITEMS = [
  { to: "/", label: "مستنداتي", icon: "▦", end: true },
  { to: "/profile", label: "الملف الشخصي", icon: "◉" },
  { to: "/status", label: "حالة النظام", icon: "◎" },
];

export default function AppLayout() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [menuOpen, setMenuOpen] = useState(false);
  const [loggingOut, setLoggingOut] = useState(false);

  // Close the mobile menu after navigating.
  useEffect(() => setMenuOpen(false), [location.pathname]);

  async function handleLogout() {
    setLoggingOut(true);
    try {
      await logout();
      navigate("/login", { replace: true });
    } finally {
      setLoggingOut(false);
    }
  }

  return (
    <div className="app-layout">
      <header className="topbar">
        <button
          type="button"
          className="icon-btn menu-toggle"
          aria-label="فتح القائمة"
          aria-expanded={menuOpen}
          onClick={() => setMenuOpen((open) => !open)}
        >
          ☰
        </button>
        <div className="brand">
          <span className="brand-logo">C</span>
          <span className="brand-name">CollabSpace</span>
        </div>
        <div className="topbar-user">
          <span className="topbar-name">{user.display_name}</span>
          <Avatar name={user.display_name} color={user.color} />
        </div>
      </header>

      {menuOpen && <div className="sidebar-backdrop" onClick={() => setMenuOpen(false)} />}

      <nav className={`sidebar ${menuOpen ? "sidebar--open" : ""}`} aria-label="القائمة الرئيسية">
        <ul className="nav-list">
          {NAV_ITEMS.map((item) => (
            <li key={item.to}>
              <NavLink to={item.to} end={item.end} className="nav-link">
                <span className="nav-icon" aria-hidden="true">
                  {item.icon}
                </span>
                {item.label}
              </NavLink>
            </li>
          ))}
        </ul>
        <button type="button" className="nav-link nav-logout" onClick={handleLogout} disabled={loggingOut}>
          <span className="nav-icon" aria-hidden="true">
            ⎋
          </span>
          {loggingOut ? "جارٍ تسجيل الخروج…" : "تسجيل الخروج"}
        </button>
      </nav>

      <main className="app-content">
        <Outlet />
      </main>
    </div>
  );
}
