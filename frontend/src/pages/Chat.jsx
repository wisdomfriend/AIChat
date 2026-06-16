import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Alert, Button, Card, Space, Spin, Typography, message } from "antd";
import { LogoutOutlined, MessageOutlined } from "@ant-design/icons";
import { apiFetch } from "../api/client";
import { clearAuth, getStoredUser } from "../api/auth";

const { Title, Paragraph, Text } = Typography;

export default function Chat() {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [user, setUser] = useState(getStoredUser());
  const [sessions, setSessions] = useState([]);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      setLoading(true);
      try {
        const meData = await apiFetch("/api/auth/me");
        const sessionData = await apiFetch("/api/sessions");
        if (!cancelled) {
          setUser(meData.user);
          setSessions(sessionData.sessions || []);
        }
      } catch (error) {
        if (!cancelled) {
          message.error(error instanceof Error ? error.message : "加载失败");
          navigate("/login", { replace: true });
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }

    void load();
    return () => {
      cancelled = true;
    };
  }, [navigate]);

  function handleLogout() {
    clearAuth();
    message.success("已登出");
    navigate("/login", { replace: true });
  }

  if (loading) {
    return (
      <div className="page-shell">
        <Spin tip="加载中..." />
      </div>
    );
  }

  return (
    <div className="page-shell chat-shell">
      <Card className="hero-card chat-card" bordered={false}>
        <Space direction="vertical" size="large" style={{ width: "100%" }}>
          <Space align="center" style={{ justifyContent: "space-between", width: "100%" }}>
            <Space align="center">
              <MessageOutlined style={{ fontSize: 24, color: "#667eea" }} />
              <Title level={3} style={{ margin: 0 }}>
                聊天工作台
              </Title>
            </Space>
            <Button icon={<LogoutOutlined />} onClick={handleLogout}>
              退出
            </Button>
          </Space>

          <Alert
            type="info"
            showIcon
            message="阶段 2 已完成 Bearer 认证"
            description="聊天 UI 将在阶段 3 实现。当前页面用于验证登录态与 /api/sessions 鉴权。"
          />

          <Paragraph>
            当前用户：<Text strong>{user?.username}</Text>
            {user?.is_admin ? <Text type="warning">（管理员）</Text> : null}
          </Paragraph>

          <Paragraph type="secondary">
            已加载会话数：{sessions.length}
          </Paragraph>

          <Button type="primary" disabled>
            开始聊天（阶段 3 开放）
          </Button>
        </Space>
      </Card>
    </div>
  );
}
