/**
 * 聊天侧栏：会话搜索 + 历史列表。
 */
import { useMemo, useState } from "react";
import { Input } from "antd";
import { SearchOutlined } from "@ant-design/icons";
import CollapsibleSidebar from "../layout/CollapsibleSidebar";

export default function SessionSidebar({
  collapsed,
  onToggle,
  user,
  sessions,
  sessionId,
  onNewChat,
  onSelectSession,
  onLogout,
}) {
  const [keyword, setKeyword] = useState("");

  const filteredSessions = useMemo(() => {
    const q = keyword.trim().toLowerCase();
    if (!q) {
      return sessions;
    }
    return sessions.filter((s) => (s.title || `会话 ${s.id}`).toLowerCase().includes(q));
  }, [sessions, keyword]);

  return (
    <CollapsibleSidebar
      collapsed={collapsed}
      onToggle={onToggle}
      user={user}
      onLogout={onLogout}
      selectedKey="chat"
      showNewChat
      onNewChat={onNewChat}
    >
      <div className="app-sessions-section">
        <Input
          allowClear
          size="small"
          prefix={<SearchOutlined />}
          placeholder="搜索对话..."
          value={keyword}
          onChange={(e) => setKeyword(e.target.value)}
          className="app-session-search"
        />
        <div className="app-sessions-header">
          <span>对话记录</span>
          <span className="app-sessions-count">{filteredSessions.length}</span>
        </div>
        <div className="app-sessions-list">
          {filteredSessions.length === 0 ? (
            <div className="app-sessions-empty">
              {keyword ? "无匹配对话" : "暂无历史对话"}
            </div>
          ) : (
            filteredSessions.map((s) => (
              <button
                key={s.id}
                type="button"
                className={`app-session-item ${sessionId === s.id ? "active" : ""}`}
                onClick={() => onSelectSession(s.id)}
              >
                <div className="app-session-title">{s.title || `会话 ${s.id}`}</div>
              </button>
            ))
          )}
        </div>
      </div>
    </CollapsibleSidebar>
  );
}
