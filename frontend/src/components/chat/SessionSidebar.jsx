/**
 * 聊天侧栏：搜索 + 固定/最近分组（默认折叠）。
 */
import { useEffect, useMemo, useState } from "react";
import { Input } from "antd";
import { PushpinOutlined, RightOutlined, SearchOutlined } from "@ant-design/icons";
import CollapsibleSidebar from "../layout/CollapsibleSidebar";

function SessionGroup({ title, count, collapsed, onToggle, children, emptyText }) {
  return (
    <div className="app-session-group">
      <button type="button" className="app-session-group-header" onClick={onToggle}>
        <RightOutlined className={`app-session-group-arrow ${collapsed ? "" : "expanded"}`} />
        <span className="app-session-group-title">{title}</span>
        <span className="app-sessions-count">{count}</span>
      </button>
      {!collapsed && (
        <div className="app-sessions-list app-session-group-list">
          {count === 0 ? <div className="app-sessions-empty">{emptyText}</div> : children}
        </div>
      )}
    </div>
  );
}

function SessionItem({ session, active, onSelect }) {
  return (
    <button
      type="button"
      className={`app-session-item ${active ? "active" : ""}`}
      onClick={() => onSelect(session.id)}
    >
      <div className="app-session-title">
        {session.is_pinned && <PushpinOutlined className="app-session-pin" />}
        <span>{session.title || `会话 ${session.id}`}</span>
      </div>
    </button>
  );
}

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
  const [pinnedCollapsed, setPinnedCollapsed] = useState(true);
  const [recentCollapsed, setRecentCollapsed] = useState(true);

  const { pinnedSessions, recentSessions } = useMemo(() => {
    const q = keyword.trim().toLowerCase();
    const filtered = q
      ? sessions.filter((s) => (s.title || `会话 ${s.id}`).toLowerCase().includes(q))
      : sessions;

    return {
      pinnedSessions: filtered.filter((s) => Boolean(s.is_pinned)),
      recentSessions: filtered.filter((s) => !s.is_pinned),
    };
  }, [sessions, keyword]);

  const hasAny = pinnedSessions.length > 0 || recentSessions.length > 0;

  useEffect(() => {
    if (recentSessions.length > 0) {
      setRecentCollapsed(false);
    }
  }, [recentSessions.length]);

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

        {!hasAny ? (
          <div className="app-sessions-empty">{keyword ? "无匹配对话" : "暂无历史对话"}</div>
        ) : (
          <div className="app-sessions-scroll">
            {pinnedSessions.length > 0 && (
              <SessionGroup
                title="已固定"
                count={pinnedSessions.length}
                collapsed={pinnedCollapsed}
                onToggle={() => setPinnedCollapsed((v) => !v)}
                emptyText="暂无固定对话"
              >
                {pinnedSessions.map((s) => (
                  <SessionItem
                    key={s.id}
                    session={s}
                    active={sessionId === s.id}
                    onSelect={onSelectSession}
                  />
                ))}
              </SessionGroup>
            )}

            <SessionGroup
              title="最近对话"
              count={recentSessions.length}
              collapsed={recentCollapsed}
              onToggle={() => setRecentCollapsed((v) => !v)}
              emptyText="暂无对话"
            >
              {recentSessions.map((s) => (
                <SessionItem
                  key={s.id}
                  session={s}
                  active={sessionId === s.id}
                  onSelect={onSelectSession}
                />
              ))}
            </SessionGroup>
          </div>
        )}
      </div>
    </CollapsibleSidebar>
  );
}
