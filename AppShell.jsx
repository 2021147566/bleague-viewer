import { NavLink, Outlet, useLocation } from "react-router-dom";
import { useRosterConference } from "./RosterConferenceContext.jsx";
import { CONFERENCES } from "./rosterConfig.js";

const LINKS = [
  { to: "/", label: "B.PREMIER 로스터", end: true },
  { to: "/calc", label: "2빅 슬롯 계산", end: false },
];

export default function AppShell() {
  const location = useLocation();
  const { conf, setConf } = useRosterConference();
  const onRoster = location.pathname === "/" || location.pathname === "";

  return (
    <div className="site-shell">
      <header className="site-nav">
        <NavLink to="/" className="site-brand">
          <span className="icon" aria-hidden="true">
            🏀
          </span>
          <span className="site-brand-text">삼성 × B.League</span>
        </NavLink>

        {onRoster && (
          <div className="site-conf-switch" role="group" aria-label="컨퍼런스">
            {Object.entries(CONFERENCES).map(([key, { label }]) => (
              <button
                key={key}
                type="button"
                className={conf === key ? "active" : ""}
                onClick={() => setConf(key)}
              >
                {label}
              </button>
            ))}
          </div>
        )}

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
