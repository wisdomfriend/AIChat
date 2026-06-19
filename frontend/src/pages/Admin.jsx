/**
 * 系统管理页（admin）：全局 Token 统计与最近调用记录。
 */
import { useEffect, useMemo, useState } from "react";
import { Card, Col, Row, Spin, Statistic, Table, Typography, message } from "antd";
import RequireAdmin from "../components/RequireAdmin";
import AppLayout from "../components/layout/AppLayout";
import { fetchAdminStats } from "../api/stats";

const { Text } = Typography;

const PERIOD_LABELS = {
  today: "今日",
  week: "本周",
  month: "本月",
  total: "累计",
};

function PeriodStats({ periodKey, data }) {
  return (
    <Card
      className="gov-page-card"
      title={`${PERIOD_LABELS[periodKey]}统计`}
      bordered={false}
      size="small"
    >
      <Row gutter={[8, 8]}>
        <Col span={12}>
          <Statistic title="Prompt" value={data.prompt} valueStyle={{ fontSize: 18 }} />
        </Col>
        <Col span={12}>
          <Statistic title="Completion" value={data.completion} valueStyle={{ fontSize: 18 }} />
        </Col>
        <Col span={12}>
          <Statistic
            title="Total"
            value={data.total}
            valueStyle={{ fontSize: 20, color: "#0050b3" }}
          />
        </Col>
        <Col span={12}>
          <Statistic title="请求次数" value={data.count} valueStyle={{ fontSize: 18 }} />
        </Col>
      </Row>
    </Card>
  );
}

function AdminPage() {
  const [loading, setLoading] = useState(true);
  const [stats, setStats] = useState({});
  const [recentUsage, setRecentUsage] = useState([]);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      try {
        const data = await fetchAdminStats();
        if (!cancelled) {
          setStats(data.stats || {});
          setRecentUsage(data.recent_usage || []);
        }
      } catch (error) {
        if (!cancelled) {
          message.error(error instanceof Error ? error.message : "加载管理数据失败");
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

  const columns = useMemo(
    () => [
      {
        title: "时间",
        dataIndex: "request_time",
        key: "request_time",
        width: 180,
        render: (value) => (value ? value.replace("T", " ").slice(0, 19) : "-"),
      },
      {
        title: "用户 ID",
        dataIndex: "user_id",
        key: "user_id",
        width: 90,
      },
      {
        title: "Prompt",
        dataIndex: "prompt_tokens",
        key: "prompt_tokens",
        width: 100,
      },
      {
        title: "Completion",
        dataIndex: "completion_tokens",
        key: "completion_tokens",
        width: 110,
      },
      {
        title: "Total",
        dataIndex: "total_tokens",
        key: "total_tokens",
        width: 100,
        render: (value) => <Text strong>{value}</Text>,
      },
      {
        title: "模型",
        dataIndex: "model",
        key: "model",
      },
    ],
    []
  );

  return (
    <AppLayout title="系统管理">
      {loading ? (
        <div style={{ textAlign: "center", padding: 80 }}>
          <Spin tip="加载管理数据..." />
        </div>
      ) : (
        <>
          <h3 className="gov-section-title">全局 Token 统计</h3>
          <Row gutter={[16, 16]}>
            {["today", "week", "month", "total"].map((key) => (
              <Col xs={24} sm={12} xl={6} key={key}>
                <PeriodStats periodKey={key} data={stats[key] || {}} />
              </Col>
            ))}
          </Row>

          <Card
            className="gov-page-card"
            title="最近使用记录"
            bordered={false}
            style={{ marginTop: 16 }}
          >
            <Table
              rowKey="id"
              size="middle"
              columns={columns}
              dataSource={recentUsage}
              pagination={{ pageSize: 10, showSizeChanger: false }}
              locale={{ emptyText: "暂无使用记录" }}
              scroll={{ x: 800 }}
            />
          </Card>
        </>
      )}
    </AppLayout>
  );
}

export default function Admin() {
  return (
    <RequireAdmin>
      <AdminPage />
    </RequireAdmin>
  );
}
