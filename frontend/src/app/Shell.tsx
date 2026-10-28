import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Car, House, LogOut, Plus } from "lucide-react";
import { Link, NavLink, Outlet, useMatch } from "react-router";
import { api, type User } from "../api/client";
import { useVehicles } from "../api/hooks";
import { Photo } from "../components/Photo";
import { PlateBadge } from "../components/PlateBadge";

export function Shell({ user }: { user: User }) {
  const qc = useQueryClient();
  const vehicles = useVehicles();
  const onVehicle = useMatch("/vehicles/:id");
  const logout = useMutation({
    mutationFn: () => api("/auth/logout", "POST"),
    onSuccess: () => qc.setQueryData(["me"], null),
  });
  // Only sections that exist. Add Records, Reminders, ... here as they are built.
  // "/" redirects to the last vehicle, so Home also counts as active on any vehicle page.
  const links = (
    <>
      <NavLink to="/" end className={({ isActive }) => `nav-link${isActive || onVehicle ? " active" : ""}`}>
        <House size={20} aria-hidden="true" />
        Home
      </NavLink>
      <NavLink to="/garage" className="nav-link">
        <Car size={20} aria-hidden="true" />
        Garage
      </NavLink>
    </>
  );
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
        <nav aria-label="Garage">
          <div className="label" style={{ padding: "0 0.75rem 0.25rem" }}>
            Garage
          </div>
          <ul className="side-vehicles">
            {vehicles.data?.map((v) => (
              <li key={v.id}>
                <NavLink to={`/vehicles/${v.id}`} className={({ isActive }) => `side-veh${isActive ? " on" : ""}`}>
                  <span className="thumb">
                    <Photo id={v.photo_attachment_id} />
                  </span>
                  <span className="side-name">{v.name}</span>
                  <PlateBadge plate={v.plate} />
                </NavLink>
              </li>
            ))}
          </ul>
          <Link to="/vehicles/new" className="nav-link">
            <Plus size={20} aria-hidden="true" />
            Add vehicle
          </Link>
        </nav>
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
