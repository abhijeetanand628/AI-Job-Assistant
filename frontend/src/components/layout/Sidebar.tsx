import type { ReactNode } from "react";
import { Icon } from "../ui/Icon";
import type { Profile } from "../../types";
export type View = "search" | "chat" | "applications" | "profile";
export function Sidebar({
  view,
  setView,
  profile,
  count,
  onClose,
}: {
  view: View;
  setView: (view: View) => void;
  profile: Profile;
  count: number;
  onClose: () => void;
}) {
  return (
    <aside className="sidebar" aria-label="App navigation">
      <div className="sidebar-top">
        <div className="brand">
          <span className="logo-mark">
            <Icon name="spark" />
          </span>
          <span>AI Job Assistant</span>
        </div>
        <button className="mobile-close" onClick={onClose} aria-label="Close navigation">
          <Icon name="close" />
        </button>
      </div>
      <nav className="nav-list" aria-label="Primary">
        {(
          [
            ["search", "search", "Job Search"],
            ["chat", "message", "Assistant chat"],
            ["applications", "briefcase", "Applications"],
            ["profile", "user", "Profile"],
          ] as [View, "search" | "briefcase" | "user" | "message", string][]
        ).map(([key, icon, label]) => (
          <button
            key={key}
            className={view === key ? "active" : ""}
            onClick={() => setView(key)}
          >
            <Icon name={icon} />
            <span>{label}</span>
            {key === "applications" && count > 0 && <b>{count}</b>}
          </button>
        ))}
      </nav>
      <div className="sidebar-spacer" />
      <div className="profile-mini">
        <span className="avatar">
          {profile.name
            .split(/\s+/)
            .map((s) => s[0])
            .join("")
            .slice(0, 2)
            .toUpperCase()}
        </span>
        <span>
          <strong>{profile.name}</strong>
          <small>{profile.email}</small>
        </span>
      </div>
    </aside>
  );
}

export function PageHeader({
  title,
  subtitle,
  children,
}: {
  title: string;
  subtitle: string;
  children?: ReactNode;
}) {
  return (
    <header className="topbar">
      <div>
        <div className="title-row">
          <h1>{title}</h1>
        </div>
        <p>{subtitle}</p>
      </div>
      <div className="top-actions">{children}</div>
    </header>
  );
}
