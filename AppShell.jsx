import { NavLink, Outlet } from "react-router-dom";

const LINKS = [
  { to: "/", label: "B.PREMIER 로스터", end: true },
  { to: "/calc", label: "2빅 슬롯 계산", end: false },
];

export default function AppShell() {
  return (
    <div className="site-shell">
      <header className="site-nav">
        <NavLink to="/" className="site-brand">
          <span className="icon" aria-hidden="true">
            🏀
          </span>
          <span className="site-brand-text">삼성 × B.League</span>
        </NavLink>
        <nav className="site-nav-links" aria-label="주 메뉴">
          {LINKS.map(({ to, label, end }) => (
            <NavLink
              key={to}
              to={to}
              end={end}
              className={({ isActive }) => `site-nav-link${isActive ? " active" : ""}`}
            >
              {label}
            </NavLink>
          ))}
        </nav>
      </header>
      <main className="site-main">
        <Outlet />
      </main>
    </div>
  );
}
