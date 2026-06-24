/**
 * 知识库详情布局 — 侧栏 + 子路由出口。
 */
import { useCallback, useEffect, useState } from "react";
import { Outlet, useNavigate, useParams } from "react-router-dom";
import { Spin, message } from "antd";
import AppLayout from "../../components/layout/AppLayout";
import { fetchKnowledgeBases } from "../../api/knowledge";
import KnowledgeSidebar from "./KnowledgeSidebar";
import "../../styles/knowledge.css";

export default function KnowledgeDetailLayout() {
  const { kbId } = useParams();
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [kb, setKb] = useState(null);

  const loadKb = useCallback(async () => {
    const list = await fetchKnowledgeBases();
    const found = list.find((item) => String(item.id) === String(kbId));
    if (!found) {
      message.error("知识库不存在");
      navigate("/knowledge", { replace: true });
      return null;
    }
    setKb(found);
    return found;
  }, [kbId, navigate]);

  useEffect(() => {
    let cancelled = false;
    async function boot() {
      setLoading(true);
      try {
        await loadKb();
      } catch (error) {
        if (!cancelled) {
          message.error(error instanceof Error ? error.message : "加载失败");
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }
    void boot();
    return () => {
      cancelled = true;
    };
  }, [loadKb]);

  if (loading) {
    return (
      <AppLayout title="知识库">
        <div className="kb-page">
          <div className="kb-loading">
            <Spin tip="加载中..." />
          </div>
        </div>
      </AppLayout>
    );
  }

  return (
    <AppLayout title="知识库">
      <div className="kb-page kb-detail-layout">
        <KnowledgeSidebar kb={kb} />
        <div className="kb-detail-main">
          <Outlet context={{ kb, refreshKb: loadKb }} />
        </div>
      </div>
    </AppLayout>
  );
}
