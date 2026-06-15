import { useEffect, useState } from "react";
import { Alert, Button, Card, Space, Spin, Typography } from "antd";
import { ApiOutlined, RocketOutlined } from "@ant-design/icons";
import { apiFetch } from "../api/client";

const { Title, Paragraph, Text } = Typography;

export default function Home() {
  const [loading, setLoading] = useState(true);
  const [health, setHealth] = useState(null);
  const [supported, setSupported] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;

    async function load() {
      setLoading(true);
      setError("");
      try {
        const [healthData, supportedData] = await Promise.all([
          apiFetch("/health"),
          apiFetch("/api/files/supported"),
        ]);
        if (!cancelled) {
          setHealth(healthData);
          setSupported(supportedData);
        }
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : String(err));
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
  }, []);

  return (
    <div className="page-shell">
      <Card className="hero-card" bordered={false}>
        <Space direction="vertical" size="large" style={{ width: "100%" }}>
          <Space align="center">
            <RocketOutlined style={{ fontSize: 28, color: "#667eea" }} />
            <Title level={2} style={{ margin: 0 }}>
              AIChat React 迁移
            </Title>
          </Space>

          <Paragraph type="secondary" style={{ marginBottom: 0 }}>
            阶段 1 已完成：单 Nginx 统一入口、React 占位页、Redis 仅限流、Flask API 反代。
            下一阶段将实现 Bearer Token 认证与聊天页。
          </Paragraph>

          {loading ? (
            <div className="center-row">
              <Spin tip="正在检查后端连通性..." />
            </div>
          ) : error ? (
            <Alert type="error" showIcon message="后端连通性检查失败" description={error} />
          ) : (
            <Space direction="vertical" size="middle" style={{ width: "100%" }}>
              <Alert
                type="success"
                showIcon
                message="后端连通正常"
                description={
                  <Space direction="vertical" size={4}>
                    <Text>
                      <ApiOutlined /> /health: {health?.status || "unknown"}
                    </Text>
                    <Text>
                      /api/files/supported: 支持 {supported?.extensions?.length || 0} 种扩展名，
                      最大 {supported?.max_size_mb || "-"} MB
                    </Text>
                  </Space>
                }
              />
              <Button type="primary" disabled>
                聊天功能（阶段 3 开放）
              </Button>
            </Space>
          )}
        </Space>
      </Card>
    </div>
  );
}
