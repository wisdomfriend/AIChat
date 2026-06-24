/**
 * 知识库详情侧栏。
 */
import { useNavigate, useParams, useLocation } from "react-router-dom";
import {
  DatabaseOutlined,
  FileSearchOutlined,
  ArrowLeftOutlined,
} from "@ant-design/icons";
import { Button, Card } from "antd";
import { formatDate, kbInitial } from "./utils";

const NAV_ITEMS = [
  { key: "files", label: "文件列表", icon: DatabaseOutlined },
  { key: "testing", label: "检索测试", icon: FileSearchOutlined },
];

export default function KnowledgeSidebar({ kb }) {
  const navigate = useNavigate();
  const { kbId } = useParams();
  const location = useLocation();

  const activeKey = location.pathname.includes("/testing") ? "testing" : "files";

  if (!kb) {
    return null;
  }

  return (
    <aside className="kb-detail-sidebar">
      <Card className="gov-page-card kb-detail-sidebar-card" bordered={false}>
        <Button
          type="link"
          icon={<ArrowLeftOutlined />}
          onClick={() => navigate("/knowledge")}
          style={{ padding: 0, marginBottom: 16, height: "auto" }}
        >
          返回列表
        </Button>

        <div className="kb-detail-sidebar-info">
          <div className="kb-card-avatar">{kbInitial(kb.name)}</div>
          <div className="kb-detail-sidebar-name">{kb.name}</div>
          <div className="kb-detail-sidebar-meta">
            <div>{kb.document_count || 0} 个文件</div>
            <div>创建于 {formatDate(kb.created_at)}</div>
          </div>
        </div>

        <nav className="kb-detail-nav">
          {NAV_ITEMS.map((item) => (
            <button
              key={item.key}
              type="button"
              className={`kb-detail-nav-item ${activeKey === item.key ? "active" : ""}`}
              onClick={() => navigate(`/knowledge/${kbId}/${item.key}`)}
            >
              <item.icon />
              <span>{item.label}</span>
            </button>
          ))}
        </nav>
      </Card>
    </aside>
  );
}
