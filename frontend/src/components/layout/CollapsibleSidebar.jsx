/**
 * 可折叠侧栏（Chat / Dashboard / Admin 共用）。
 */
import { useNavigate } from "react-router-dom";
import { Avatar, Button, Dropdown, Tooltip } from "antd";
import {
  BarChartOutlined,
  LogoutOutlined,
  MenuFoldOutlined,
  MenuUnfoldOutlined,
  PlusOutlined,
  SettingOutlined,
} from "@ant-design/icons";
import "../../styles/app-shell.css";

const DEFAULT_NAV = [{ key: "chat", label: "智能对话", path: "/chat" }];

const INTERACTIVE_SELECTOR = "button, .ant-btn, .ant-dropdown-trigger, a, input, textarea, select";

export default function CollapsibleSidebar({
  collapsed,
  onToggle,
  user,
  onLogout,
  selectedKey = "chat",
  onNewChat,
  showNewChat = false,
  children,
}) {
  const navigate = useNavigate();

  const navItems = [...DEFAULT_NAV];
  if (user?.is_admin) {
    navItems.push(
      { key: "dashboard", label: "数据统计", path: "/dashboard" },
      { key: "admin", label: "系统管理", path: "/admin" }
    );
  }

  const userMenuItems = [
    ...(user?.is_admin
      ? [
          {
            key: "dashboard",
            icon: <BarChartOutlined />,
            label: "数据统计",
            onClick: () => navigate("/dashboard"),
          },
          {
            key: "admin",
            icon: <SettingOutlined />,
            label: "系统管理",
            onClick: () => navigate("/admin"),
          },
          { type: "divider" },
        ]
      : []),
    {
      key: "logout",
      icon: <LogoutOutlined />,
      label: "退出登录",
      onClick: onLogout,
    },
  ];

  function handleNav(path) {
    navigate(path);
  }

  function handleAsideClick(e) {
    if (!collapsed) {
      return;
    }
    if (e.target.closest(INTERACTIVE_SELECTOR)) {
      return;
    }
    onToggle();
  }

  return (
    <aside
      className={`app-sidebar ${collapsed ? "app-sidebar-collapsed" : ""}`}
      onClick={handleAsideClick}
    >
      <div className="app-sidebar-top">
        {!collapsed && (
          <div className="app-sidebar-brand">
            <div className="app-sidebar-mark">AI</div>
            <div className="app-sidebar-brand-title">智能助手</div>
          </div>
        )}
        <Tooltip title={collapsed ? "展开侧栏" : "收起侧栏"} placement="right">
          <Button
            type="text"
            className="app-sidebar-icon-btn"
            icon={collapsed ? <MenuUnfoldOutlined /> : <MenuFoldOutlined />}
            onClick={(e) => {
              e.stopPropagation();
              onToggle();
            }}
          />
        </Tooltip>
      </div>

      {showNewChat && (
        <div className="app-sidebar-actions">
          <Tooltip title="新建对话" placement="right">
            <Button
              type={collapsed ? "text" : "default"}
              block={!collapsed}
              icon={<PlusOutlined />}
              onClick={(e) => {
                e.stopPropagation();
                onNewChat();
              }}
              className={`app-new-chat-btn ${collapsed ? "app-sidebar-icon-btn app-new-chat-btn-collapsed" : ""}`}
            >
              {!collapsed && "新建对话"}
            </Button>
          </Tooltip>
        </div>
      )}

      {!collapsed && navItems.length > 1 && (
        <div className="app-sidebar-nav">
          {navItems.map((item) => (
            <button
              key={item.key}
              type="button"
              className={`app-nav-item ${selectedKey === item.key ? "active" : ""}`}
              onClick={() => handleNav(item.path)}
            >
              {item.label}
            </button>
          ))}
        </div>
      )}

      {!collapsed && children}

      {(!children || collapsed) && <div className="app-sidebar-spacer" />}

      <div className="app-sidebar-bottom">
        <Dropdown menu={{ items: userMenuItems }} placement="topLeft" trigger={["click"]}>
          <button type="button" className="app-sidebar-user-btn" onClick={(e) => e.stopPropagation()}>
            <Avatar className="app-user-avatar" size={collapsed ? 32 : 36}>
              {(user?.username || "?")[0]?.toUpperCase()}
            </Avatar>
            {!collapsed && (
              <div className="app-sidebar-user-text">
                <div className="app-user-name">{user?.username}</div>
                <div className="app-user-role">{user?.is_admin ? "管理员" : "用户"}</div>
              </div>
            )}
          </button>
        </Dropdown>
      </div>
    </aside>
  );
}
