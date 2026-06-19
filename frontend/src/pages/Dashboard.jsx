/**
 * 数据统计页（admin）：个人 Token 用量概览。
 */
import { useEffect, useState } from "react";
import { Card, Col, Row, Spin, Statistic, Typography, message } from "antd";
import {
  CalendarOutlined,
  FieldTimeOutlined,
  FundOutlined,
  PieChartOutlined,
} from "@ant-design/icons";
import RequireAdmin from "../components/RequireAdmin";
import AppLayout from "../components/layout/AppLayout";
import { fetchUserStats } from "../api/stats";
import { getStoredUser } from "../api/auth";

const { Paragraph, Text } = Typography;

function StatCards({ stats }) {
  const items = [
    { title: "今日使用", value: stats.today, icon: <CalendarOutlined /> },
    { title: "本周使用", value: stats.week, icon: <FieldTimeOutlined /> },
    { title: "本月使用", value: stats.month, icon: <PieChartOutlined /> },
    { title: "累计使用", value: stats.total, icon: <FundOutlined /> },
  ];

  return (
    <Row gutter={[16, 16]}>
      {items.map((item) => (
        <Col xs={24} sm={12} lg={6} key={item.title}>
          <Card className="gov-page-card gov-stat-card" bordered={false}>
            <Statistic
              title={item.title}
              value={item.value}
              suffix="tokens"
              prefix={item.icon}
              valueStyle={{ color: "#0050b3" }}
            />
          </Card>
        </Col>
      ))}
    </Row>
  );
}

function DashboardPage() {
  const user = getStoredUser();
  const [loading, setLoading] = useState(true);
  const [stats, setStats] = useState({ today: 0, week: 0, month: 0, total: 0 });

  useEffect(() => {
    let cancelled = false;

    async function load() {
      try {
        const data = await fetchUserStats();
        if (!cancelled) {
          setStats(data.stats || {});
        }
      } catch (error) {
        if (!cancelled) {
          message.error(error instanceof Error ? error.message : "加载统计失败");
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
    <AppLayout title="数据统计">
      {loading ? (
        <div style={{ textAlign: "center", padding: 80 }}>
          <Spin tip="加载统计数据..." />
        </div>
      ) : (
        <>
          <Card className="gov-page-card" bordered={false} style={{ marginBottom: 16 }}>
            <Paragraph style={{ marginBottom: 4 }}>
              欢迎，<Text strong>{user?.username}</Text>
            </Paragraph>
            <Text type="secondary">以下为您的 Token 使用统计概览，数据来源于系统调用记录。</Text>
          </Card>

          <h3 className="gov-section-title">Token 使用统计</h3>
          <StatCards stats={stats} />

          <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
            <Col xs={24} lg={8}>
              <Card className="gov-page-card" title="系统状态" bordered={false}>
                <Paragraph>Flask 应用运行正常</Paragraph>
                <Paragraph>MySQL 数据库连接正常</Paragraph>
                <Paragraph>Nginx 反向代理已配置</Paragraph>
              </Card>
            </Col>
            <Col xs={24} lg={8}>
              <Card className="gov-page-card" title="技术架构" bordered={false}>
                <Paragraph>Python Flask + React</Paragraph>
                <Paragraph>MySQL 8.0 + Redis 7</Paragraph>
                <Paragraph>LangChain + DeepSeek API</Paragraph>
              </Card>
            </Col>
            <Col xs={24} lg={8}>
              <Card className="gov-page-card" title="功能模块" bordered={false}>
                <Paragraph>用户认证与权限管理</Paragraph>
                <Paragraph>智能对话与 Agent 模式</Paragraph>
                <Paragraph>Token 用量统计分析</Paragraph>
              </Card>
            </Col>
          </Row>
        </>
      )}
    </AppLayout>
  );
}

export default function Dashboard() {
  return (
    <RequireAdmin>
      <DashboardPage />
    </RequireAdmin>
  );
}
