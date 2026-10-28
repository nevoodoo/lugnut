import { Bell, Car, ChartNoAxesColumn, FileText, House, List, LogOut, Plus, Settings, X } from "lucide-react";
import { useRef } from "react";
import { Link, NavLink, Outlet, useMatch } from "react-router";
import type { User } from "../api/client";
import { useLogout, useVehicles } from "../api/hooks";
import { Photo } from "../components/Photo";
import { PlateBadge } from "../components/PlateBadge";
import { TypePicker } from "../components/TypePicker";
import { getLastVehicle } from "../lib/lastVehicle";

export function Shell({ user }: { user: User }) {
  const vehicles = useVehicles();
  const onVehicle = useMatch("/vehicles/:id");
  const inVehicle = useMatch("/vehicles/:id/*");
  const onRecord = useMatch("/records/:id");
  const picker = useRef<HTMLDialogElement>(null);
  // The vehicle on screen, else the last one viewed, else the first. "+" and Records act on it.
  const ids = vehicles.data?.map((v) => v.id) ?? [];
  const current = [Number(inVehicle?.params.id), getLastVehicle()].find((n) => n !== null && ids.includes(n)) ?? ids[0];
  const logout = useLogout();
  // Only sections that exist. Add the rest here as they are built.
  // "/" redirects to the last vehicle, so Home also counts as active on any vehicle page.
  const home = (
    <NavLink to="/" end className={({ isActive }) => `nav-link${isActive || onVehicle ? " active" : ""}`}>
      <House size={20} aria-hidden="true" />
      Home
    </NavLink>
  );
  const records = current !== undefined && (
    <NavLink to={`/vehicles/${current}/records`} className={({ isActive }) => `nav-link${isActive || onRecord ? " active" : ""}`}>
      <List size={20} aria-hidden="true" />
      Records
    </NavLink>
  );
  const insights = current !== undefined && (
    <NavLink to={`/vehicles/${current}/insights`} className="nav-link">
      <ChartNoAxesColumn size={20} aria-hidden="true" />
      Insights
    </NavLink>
  );
  const reminders = (
    <NavLink to="/reminders" className="nav-link">
      <Bell size={20} aria-hidden="true" />
      Reminders
    </NavLink>
  );
  const garage = (
    <NavLink to="/garage" className="nav-link">
      <Car size={20} aria-hidden="true" />
      Garage
    </NavLink>
  );
  const documents = (
    <NavLink to="/documents" className="nav-link">
      <FileText size={20} aria-hidden="true" />
      Documents
    </NavLink>
  );
  const settings = (
    <NavLink to="/settings" className="nav-link">
      <Settings size={20} aria-hidden="true" />
      Settings
    </NavLink>
  );
  const add = (className: string, text?: string) =>
    current !== undefined && (
      <button className={className} onClick={() => picker.current?.showModal()} aria-label={text ? undefined : "Add record"}>
        <Plus size={text ? 18 : 26} aria-hidden="true" />
        {text}
      </button>
    );
  const name = vehicles.data?.find((v) => v.id === current)?.name;
  const signOut = (
    <button className="icon-btn" onClick={() => logout.mutate()} aria-label={`Sign out ${user.username}`}>
      <LogOut size={20} aria-hidden="true" />
    </button>
  );

  return (
    <div className="shell">
      <header className="topbar">
        <span className="brand">Lugnut</span>
        <div className="actions">
          <NavLink to="/settings" className="icon-btn" aria-label="Settings">
            <Settings size={20} aria-hidden="true" />
          </NavLink>
          {signOut}
        </div>
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
          {home}
          {records}
          {insights}
          {reminders}
          {documents}
          {garage}
          {settings}
        </nav>
        <div className="spacer">
          {add("btn primary add-record", "Add record")}
          <button className="btn" onClick={() => logout.mutate()}>
            <LogOut size={18} aria-hidden="true" /> Sign out
          </button>
        </div>
      </aside>
      <main className="main">
        <Outlet />
      </main>
      <nav className="bottombar" aria-label="Sections">
        {home}
        {records}
        {add("fab")}
        {insights}
        {garage}
      </nav>
      {current !== undefined && (
        // Native modal: focus is trapped and Escape closes it; a click on the backdrop closes it too.
        <dialog
          ref={picker}
          className="picker"
          aria-labelledby="picker-title"
          onClick={(e) => e.target === e.currentTarget && e.currentTarget.close()}
        >
          <div className="picker-body">
            <div className="page-head">
              <h2 id="picker-title">Add to {name}</h2>
              <button className="icon-btn" onClick={() => picker.current?.close()} aria-label="Close">
                <X size={20} aria-hidden="true" />
              </button>
            </div>
            <TypePicker vehicleId={current} onPick={() => picker.current?.close()} />
          </div>
        </dialog>
      )}
    </div>
  );
}
