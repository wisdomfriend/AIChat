/**
 * 知识库列表页。
 */
import { useCallback, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Button, Card, Empty, Form, Input, Modal, Spin, message } from "antd";
import { PlusOutlined, SearchOutlined } from "@ant-design/icons";
import AppLayout from "../../components/layout/AppLayout";
import { createKnowledgeBase, fetchKnowledgeBases } from "../../api/knowledge";
import { formatDate, kbInitial } from "./utils";
import "../../styles/knowledge.css";

export default function KnowledgeListPage() {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [kbList, setKbList] = useState([]);
  const [keyword, setKeyword] = useState("");
  const [createOpen, setCreateOpen] = useState(false);
  const [creating, setCreating] = useState(false);
  const [form] = Form.useForm();

  const loadList = useCallback(async () => {
    const list = await fetchKnowledgeBases();
    setKbList(list);
    return list;
  }, []);

  useEffect(() => {
    let cancelled = false;
    async function boot() {
      try {
        await loadList();
      } catch (error) {
        if (!cancelled) {
          message.error(error instanceof Error ? error.message : "加载知识库失败");
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
  }, [loadList]);

  async function handleCreate(values) {
    setCreating(true);
    try {
      const kb = await createKnowledgeBase(values);
      message.success("知识库已创建");
      setCreateOpen(false);
      form.resetFields();
      await loadList();
      navigate(`/knowledge/${kb.id}/files`);
    } catch (error) {
      message.error(error instanceof Error ? error.message : "创建失败");
    } finally {
      setCreating(false);
    }
  }

  const filtered = kbList.filter((kb) => {
    if (!keyword.trim()) {
      return true;
    }
    const q = keyword.trim().toLowerCase();
    return (
      kb.name?.toLowerCase().includes(q) ||
      kb.description?.toLowerCase().includes(q)
    );
  });

  if (loading) {
    return (
      <AppLayout title="知识库">
        <div className="kb-page">
          <div className="kb-loading">
            <Spin tip="加载知识库..." />
          </div>
        </div>
      </AppLayout>
    );
  }

  return (
    <AppLayout title="知识库">
      <div className="kb-page kb-list-page">
        <Card className="gov-page-card" bordered={false}>
          <div className="kb-list-header">
            <div>
              <h2>我的知识库</h2>
              <p>创建和管理文档知识库，用于 RAG 检索增强</p>
            </div>
            <div className="kb-list-toolbar">
              <Input
                prefix={<SearchOutlined />}
                placeholder="搜索知识库"
                value={keyword}
                onChange={(e) => setKeyword(e.target.value)}
                style={{ width: 220 }}
                allowClear
              />
              <Button type="primary" icon={<PlusOutlined />} onClick={() => setCreateOpen(true)}>
                新建知识库
              </Button>
            </div>
          </div>
        </Card>

        {filtered.length === 0 ? (
          <Card className="gov-page-card" bordered={false}>
            <Empty
              description={kbList.length === 0 ? "还没有知识库，点击右上角创建" : "没有匹配的知识库"}
            />
          </Card>
        ) : (
          <div className="kb-grid">
            {filtered.map((kb) => (
              <div
                key={kb.id}
                className="kb-card"
                onClick={() => navigate(`/knowledge/${kb.id}/files`)}
              >
                <div className="kb-card-top">
                  <div className="kb-card-avatar">{kbInitial(kb.name)}</div>
                  <div className="kb-card-name">{kb.name}</div>
                </div>
                <div className="kb-card-desc">{kb.description || "暂无描述"}</div>
                <div className="kb-card-meta">
                  <span>{kb.document_count || 0} 个文件</span>
                  <span>{formatDate(kb.created_at)}</span>
                </div>
              </div>
            ))}
          </div>
        )}

        <Modal
          title="新建知识库"
          open={createOpen}
          onCancel={() => setCreateOpen(false)}
          onOk={() => form.submit()}
          confirmLoading={creating}
          destroyOnClose
        >
          <Form form={form} layout="vertical" onFinish={handleCreate}>
            <Form.Item
              name="name"
              label="名称"
              rules={[{ required: true, message: "请输入知识库名称" }]}
            >
              <Input placeholder="例如：产品手册、制度文件" maxLength={200} />
            </Form.Item>
            <Form.Item name="description" label="描述">
              <Input.TextArea rows={3} placeholder="可选，说明该知识库用途" maxLength={500} />
            </Form.Item>
          </Form>
        </Modal>
      </div>
    </AppLayout>
  );
}
