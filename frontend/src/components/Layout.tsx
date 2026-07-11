import { NavLink, Outlet } from "react-router-dom";
import { SettingsPopover } from "./SettingsPopover";
import { AlertBell } from "./AlertBell";

const NAV = [
  { to: "/", label: "About", end: true },
  { to: "/scanner", label: "Scanner", end: false },
  { to: "/screener", label: "Auto-Screener", end: false },
  { to: "/guide", label: "Guide", end: false },
  { to: "/expert", label: "Expert Corner", end: false },
];

export function Layout() {
  return (
    <div className="mesh-bg min-h-screen">
      <header className="sticky top-0 z-30 border-b border-line/70 bg-base/60 backdrop-blur-2xl">
        <div className="mx-auto flex h-[68px] max-w-[1240px] items-center gap-3 px-4 sm:px-6">
          <NavLink to="/" className="flex items-center gap-2.5">
            <span className="grid h-9 w-9 place-items-center rounded-2xl bg-gradient-to-br from-violet to-cyan text-base shadow-glow-violet">
              🏆
            </span>
            <span className="font-display text-[17px] font-bold tracking-tight">Holygrail</span>
          </NavLink>

          <nav className="ml-4 hidden items-center gap-1 rounded-2xl border border-line bg-white/[0.02] p-1 md:flex">
            {NAV.map((n) => (
              <NavLink
                key={n.to}
                to={n.to}
                end={n.end}
                className={({ isActive }) =>
                  `rounded-xl px-4 py-2 text-sm font-medium transition ${
                    isActive
                      ? "bg-white/[0.08] text-ink shadow-sm"
                      : "text-muted hover:text-ink"
                  }`
                }
              >
                {n.label}
              </NavLink>
            ))}
          </nav>

          <div className="ml-auto flex items-center gap-2">
            <AlertBell />
            <SettingsPopover />
          </div>
        </div>

        <nav className="flex items-center gap-1 border-t border-line px-3 py-2 md:hidden">
          {NAV.map((n) => (
            <NavLink
              key={n.to}
              to={n.to}
              end={n.end}
              className={({ isActive }) =>
                `flex-1 rounded-xl px-2 py-2 text-center text-xs font-semibold transition ${
                  isActive ? "bg-white/[0.08] text-ink" : "text-muted"
                }`
              }
            >
              {n.label}
            </NavLink>
          ))}
        </nav>
      </header>

      <main className="mx-auto max-w-[1240px] px-4 py-8 sm:px-6">
        <Outlet />
      </main>

      <footer className="mx-auto max-w-[1240px] px-6 pb-12 pt-6 text-center text-xs text-faint">
        Educational tool, not financial advice · Data via Yahoo Finance, cached hourly
      </footer>
    </div>
  );
}
