/**
 * 政企风格后台布局（与聊天页共用可折叠侧栏）。
 */
import { useState } from "react";
import { clearAuth, getStoredUser } from "../../api/auth";
import { useLocation, useNavigate } from "react-router-dom";
import CollapsibleSidebar from "./CollapsibleSidebar";
import "../../styles/app-shell.css";

export default function AppLayout({ title, children }) {
  const navigate = useNavigate();
  const location = useLocation();
  const user = getStoredUser();
  const [collapsed, setCollapsed] = useState(true);

  const selectedKey = location.pathname.startsWith("/knowledge")
    ? "knowledge"
    : location.pathname.startsWith("/admin")
      ? "admin"
      : location.pathname.startsWith("/dashboard")
        ? "dashboard"
        : "chat";

  function handleLogout() {
    clearAuth();
    navigate("/login", { replace: true });
  }

  return (
    <div className="app-shell">
      <CollapsibleSidebar
        collapsed={collapsed}
        onToggle={() => setCollapsed((v) => !v)}
        user={user}
        onLogout={handleLogout}
        selectedKey={selectedKey}
      />

      <main className="app-shell-main">
        <header className="app-topbar">
          <div className="app-topbar-left">
            <h1 className="app-topbar-title">{title}</h1>
          </div>
        </header>

        <div className="app-shell-content">{children}</div>
      </main>
    </div>
  );
}
