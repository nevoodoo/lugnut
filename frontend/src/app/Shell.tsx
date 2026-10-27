import { useMutation, useQueryClient } from "@tanstack/react-query";
import { House, LogOut } from "lucide-react";
import { NavLink, Outlet } from "react-router";
import { api, type User } from "../api/client";

// Only sections that exist. Add Records, Reminders, ... here as they are built.
const NAV = [{ to: "/", label: "Home", icon: House }];

export function Shell({ user }: { user: User }) {
  const qc = useQueryClient();
  const logout = useMutation({
    mutationFn: () => api("/auth/logout", "POST"),
    onSuccess: () => qc.setQueryData(["me"], null),
  });
  const links = NAV.map(({ to, label, icon: Icon }) => (
    <NavLink key={to} to={to} end className="nav-link">
      <Icon size={20} aria-hidden="true" />
      {label}
    </NavLink>
  ));
  const signOut = (
    <button className="icon-btn" onClick={() => logout.mutate()} aria-label={`Sign out ${user.username}`}>
      <LogOut size={20} aria-hidden="true" />
    </button>
  );

  return (
    <div className="shell">
      <header className="topbar">
        <span className="brand">Lugnut</span>
        {signOut}
      </header>
      <aside className="sidebar">
        <span className="brand">Lugnut</span>
        <div>
          <div className="label">Garage</div>
          <p className="garage">No vehicles yet</p>
        </div>
        <nav aria-label="Sections">
          <div className="label" style={{ padding: "0 0.75rem 0.25rem" }}>
            Sections
          </div>
          {links}
        </nav>
        <div className="spacer">
          <button className="btn" onClick={() => logout.mutate()}>
            <LogOut size={18} aria-hidden="true" /> Sign out
          </button>
        </div>
      </aside>
      <main className="main">
        <Outlet />
      </main>
      <nav className="bottombar" aria-label="Sections">
        {links}
      </nav>
    </div>
  );
}
