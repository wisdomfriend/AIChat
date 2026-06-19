/**
 * 会话侧栏：品牌、新对话、历史会话、管理导航。
 */
import { useNavigate } from "react-router-dom";
import { Button, Menu } from "antd";
import {
  BarChartOutlined,
  CommentOutlined,
  LogoutOutlined,
  PlusOutlined,
  SettingOutlined,
} from "@ant-design/icons";

export default function SessionSidebar({
  user,
  sessions,
  sessionId,
  onNewChat,
  onSelectSession,
  onLogout,
}) {
  const navigate = useNavigate();

  const navItems = [{ key: "chat", icon: <CommentOutlined />, label: "智能对话" }];
  if (user?.is_admin) {
    navItems.push(
      { key: "dashboard", icon: <BarChartOutlined />, label: "数据统计" },
      { key: "admin", icon: <SettingOutlined />, label: "系统管理" }
    );
  }

  function handleNavClick({ key }) {
    if (key === "dashboard") {
      navigate("/dashboard");
    } else if (key === "admin") {
      navigate("/admin");
    }
  }

  return (
    <aside className="sidebar">
      <div className="sidebar-brand">
        <div className="sidebar-brand-mark">AI</div>
        <div>
          <div className="sidebar-brand-title">智能政务助手</div>
          <div className="sidebar-brand-sub">AIChat 平台</div>
        </div>
      </div>

      <Menu
        theme="dark"
        mode="inline"
        selectedKeys={["chat"]}
        items={navItems}
        onClick={handleNavClick}
        className="sidebar-nav"
      />

      <div className="sidebar-header">
        <Button type="primary" block icon={<PlusOutlined />} onClick={onNewChat}>
          新对话
        </Button>
      </div>

      <div className="sidebar-content">
        <div className="user-info">
          <div className="user-avatar">{(user?.username || "?")[0]?.toUpperCase()}</div>
          <div className="user-details">
            <div className="user-name">{user?.username}</div>
            <div className="user-status">{user?.is_admin ? "管理员" : "普通用户"}</div>
          </div>
        </div>

        <div className="sessions-section">
          <div className="sessions-header">
            <h3>聊天记录</h3>
          </div>
          <div className="sessions-list">
            {sessions.length === 0 ? (
              <div className="sessions-empty">暂无会话</div>
            ) : (
              sessions.map((s) => (
                <button
                  key={s.id}
                  type="button"
                  className={`session-item ${sessionId === s.id ? "active" : ""}`}
                  onClick={() => onSelectSession(s.id)}
                >
                  <div className="session-title">{s.title || `会话 ${s.id}`}</div>
                  <div className="session-meta">{s.message_count || 0} 条消息</div>
                </button>
              ))
            )}
          </div>
        </div>
      </div>

      <div className="sidebar-footer">
        <Button block icon={<LogoutOutlined />} onClick={onLogout}>
          退出登录
        </Button>
      </div>
    </aside>
  );
}
