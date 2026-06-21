/**
 * 知识库管理页 — 创建知识库、上传文档、测试检索。
 */
import { useCallback, useEffect, useMemo, useState } from "react";
import {
  Button,
  Card,
  Empty,
  Form,
  Input,
  Modal,
  Popconfirm,
  Space,
  Spin,
  Table,
  Tag,
  Typography,
  Upload,
  message,
} from "antd";
import {
  DeleteOutlined,
  FileSearchOutlined,
  InboxOutlined,
  PlusOutlined,
  ReloadOutlined,
} from "@ant-design/icons";
import RequireAuth from "../components/RequireAuth";
import AppLayout from "../components/layout/AppLayout";
import {
  createKnowledgeBase,
  deleteKnowledgeBase,
  deleteKnowledgeDocument,
  fetchDocuments,
  fetchKnowledgeBases,
  fetchKnowledgeSupported,
  searchKnowledgeBase,
  uploadKnowledgeDocument,
} from "../api/knowledge";
import "../styles/knowledge.css";

const { Text, Paragraph } = Typography;
const { Dragger } = Upload;

const STATUS_MAP = {
  ready: { color: "success", text: "已就绪" },
  processing: { color: "processing", text: "处理中" },
  pending: { color: "default", text: "等待中" },
  failed: { color: "error", text: "失败" },
};

function formatSize(bytes) {
  if (!bytes) {
    return "-";
  }
  if (bytes < 1024) {
    return `${bytes} B`;
  }
  if (bytes < 1024 * 1024) {
    return `${(bytes / 1024).toFixed(1)} KB`;
  }
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function KnowledgePage() {
  const [loading, setLoading] = useState(true);
  const [kbList, setKbList] = useState([]);
  const [activeKbId, setActiveKbId] = useState(null);
  const [documents, setDocuments] = useState([]);
  const [docsLoading, setDocsLoading] = useState(false);
  const [supported, setSupported] = useState({ extensions: [], max_size_mb: 100 });
  const [createOpen, setCreateOpen] = useState(false);
  const [creating, setCreating] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState([]);
  const [searching, setSearching] = useState(false);
  const [form] = Form.useForm();

  const activeKb = useMemo(
    () => kbList.find((item) => item.id === activeKbId) || null,
    [kbList, activeKbId]
  );

  const loadKnowledgeBases = useCallback(async () => {
    const list = await fetchKnowledgeBases();
    setKbList(list);
    setActiveKbId((prev) => {
      if (prev && list.some((item) => item.id === prev)) {
        return prev;
      }
      return list[0]?.id ?? null;
    });
    return list;
  }, []);

  const loadDocuments = useCallback(async (kbId) => {
    if (!kbId) {
      setDocuments([]);
      return;
    }
    setDocsLoading(true);
    try {
      const list = await fetchDocuments(kbId);
      setDocuments(list);
    } finally {
      setDocsLoading(false);
    }
  }, []);

  useEffect(() => {
    let cancelled = false;

    async function boot() {
      try {
        const [list, supportedInfo] = await Promise.all([
          loadKnowledgeBases(),
          fetchKnowledgeSupported(),
        ]);
        if (cancelled) {
          return;
        }
        setSupported(supportedInfo);
        if (list[0]?.id) {
          await loadDocuments(list[0].id);
        }
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
  }, [loadDocuments, loadKnowledgeBases]);

  useEffect(() => {
    if (activeKbId) {
      void loadDocuments(activeKbId);
      setSearchResults([]);
      setSearchQuery("");
    }
  }, [activeKbId, loadDocuments]);

  async function handleCreate(values) {
    setCreating(true);
    try {
      const kb = await createKnowledgeBase(values);
      message.success("知识库已创建");
      setCreateOpen(false);
      form.resetFields();
      await loadKnowledgeBases();
      setActiveKbId(kb.id);
    } catch (error) {
      message.error(error instanceof Error ? error.message : "创建失败");
    } finally {
      setCreating(false);
    }
  }

  async function handleDeleteKb(kbId) {
    try {
      await deleteKnowledgeBase(kbId);
      message.success("知识库已删除");
      const list = await loadKnowledgeBases();
      if (!list.length) {
        setActiveKbId(null);
        setDocuments([]);
      }
    } catch (error) {
      message.error(error instanceof Error ? error.message : "删除失败");
    }
  }

  async function handleUpload(file) {
    if (!activeKbId) {
      message.warning("请先创建并选择一个知识库");
      return Upload.LIST_IGNORE;
    }
    setUploading(true);
    try {
      await uploadKnowledgeDocument(activeKbId, file);
      message.success(`${file.name} 上传成功`);
      await Promise.all([loadDocuments(activeKbId), loadKnowledgeBases()]);
    } catch (error) {
      message.error(error instanceof Error ? error.message : "上传失败");
    } finally {
      setUploading(false);
    }
    return false;
  }

  async function handleDeleteDoc(docId) {
    try {
      await deleteKnowledgeDocument(activeKbId, docId);
      message.success("文档已删除");
      await Promise.all([loadDocuments(activeKbId), loadKnowledgeBases()]);
    } catch (error) {
      message.error(error instanceof Error ? error.message : "删除失败");
    }
  }

  async function handleSearch() {
    if (!activeKbId || !searchQuery.trim()) {
      message.warning("请输入检索问题");
      return;
    }
    setSearching(true);
    try {
      const data = await searchKnowledgeBase(activeKbId, searchQuery.trim());
      setSearchResults(data.results || []);
    } catch (error) {
      message.error(error instanceof Error ? error.message : "检索失败");
    } finally {
      setSearching(false);
    }
  }

  const docColumns = [
    {
      title: "文件名",
      dataIndex: "original_filename",
      key: "original_filename",
      ellipsis: true,
    },
    {
      title: "状态",
      dataIndex: "status",
      key: "status",
      width: 100,
      render: (status) => {
        const meta = STATUS_MAP[status] || STATUS_MAP.pending;
        return <Tag color={meta.color}>{meta.text}</Tag>;
      },
    },
    {
      title: "片段数",
      dataIndex: "chunk_count",
      key: "chunk_count",
      width: 90,
    },
    {
      title: "大小",
      dataIndex: "file_size",
      key: "file_size",
      width: 100,
      render: (size) => formatSize(size),
    },
    {
      title: "操作",
      key: "actions",
      width: 80,
      render: (_, record) => (
        <Popconfirm title="确定删除该文档？" onConfirm={() => handleDeleteDoc(record.id)}>
          <Button type="text" danger icon={<DeleteOutlined />} />
        </Popconfirm>
      ),
    },
  ];

  if (loading) {
    return (
      <AppLayout title="知识库">
        <div className="kb-loading">
          <Spin tip="加载知识库..." />
        </div>
      </AppLayout>
    );
  }

  return (
    <AppLayout title="知识库">
      <div className="kb-page">
        <Card className="gov-page-card kb-sidebar" bordered={false}>
          <div className="kb-sidebar-header">
            <Text strong>我的知识库</Text>
            <Button type="primary" size="small" icon={<PlusOutlined />} onClick={() => setCreateOpen(true)}>
              新建
            </Button>
          </div>

          {kbList.length === 0 ? (
            <Empty description="暂无知识库" image={Empty.PRESENTED_IMAGE_SIMPLE} />
          ) : (
            <div className="kb-list">
              {kbList.map((kb) => (
                <div
                  key={kb.id}
                  className={`kb-list-item ${activeKbId === kb.id ? "active" : ""}`}
                  onClick={() => setActiveKbId(kb.id)}
                >
                  <div className="kb-list-item-title">{kb.name}</div>
                  <div className="kb-list-item-meta">
                    {kb.document_count || 0} 篇文档
                  </div>
                </div>
              ))}
            </div>
          )}
        </Card>

        <div className="kb-main">
          {!activeKb ? (
            <Card className="gov-page-card" bordered={false}>
              <Empty description="请先创建一个知识库" />
            </Card>
          ) : (
            <>
              <Card className="gov-page-card kb-header-card" bordered={false}>
                <div className="kb-header-row">
                  <div>
                    <Text strong style={{ fontSize: 18 }}>
                      {activeKb.name}
                    </Text>
                    {activeKb.description && (
                      <Paragraph type="secondary" style={{ marginBottom: 0, marginTop: 8 }}>
                        {activeKb.description}
                      </Paragraph>
                    )}
                  </div>
                  <Space>
                    <Button icon={<ReloadOutlined />} onClick={() => loadDocuments(activeKbId)}>
                      刷新
                    </Button>
                    <Popconfirm title="删除后不可恢复，确定继续？" onConfirm={() => handleDeleteKb(activeKbId)}>
                      <Button danger icon={<DeleteOutlined />}>
                        删除知识库
                      </Button>
                    </Popconfirm>
                  </Space>
                </div>
              </Card>

              <Card className="gov-page-card" title="上传文档" bordered={false}>
                <Dragger
                  multiple
                  showUploadList={false}
                  accept={supported.extensions?.map((ext) => `.${ext.replace(/^\./, "")}`).join(",")}
                  beforeUpload={handleUpload}
                  disabled={uploading}
                >
                  <p className="ant-upload-drag-icon">
                    <InboxOutlined />
                  </p>
                  <p className="ant-upload-text">点击或拖拽文件到此处上传</p>
                  <p className="ant-upload-hint">
                    支持 {supported.extensions?.join(", ") || "txt, md, doc, docx"}，单文件最大{" "}
                    {supported.max_size_mb || 100}MB
                  </p>
                </Dragger>
              </Card>

              <Card className="gov-page-card" title="文档列表" bordered={false}>
                <Table
                  rowKey="id"
                  size="small"
                  loading={docsLoading}
                  columns={docColumns}
                  dataSource={documents}
                  pagination={{ pageSize: 8, hideOnSinglePage: true }}
                  locale={{ emptyText: "还没有文档，请先上传" }}
                />
              </Card>

              <Card className="gov-page-card" title="检索测试" bordered={false}>
                <Space.Compact style={{ width: "100%", marginBottom: 16 }}>
                  <Input
                    placeholder="输入问题，测试向量 + BM25 混合检索"
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    onPressEnter={handleSearch}
                  />
                  <Button type="primary" icon={<FileSearchOutlined />} loading={searching} onClick={handleSearch}>
                    检索
                  </Button>
                </Space.Compact>

                {searchResults.length === 0 ? (
                  <Text type="secondary">检索结果会显示在这里，便于调试召回效果。</Text>
                ) : (
                  <div className="kb-search-results">
                    {searchResults.map((item, index) => (
                      <div key={`${item.document_id}-${item.chunk_index}-${index}`} className="kb-search-result-item">
                        <div className="kb-search-result-meta">
                          <Tag>{item.filename || "未知文档"}</Tag>
                          <Tag color="blue">片段 #{Number(item.chunk_index || 0) + 1}</Tag>
                          {item.rerank_score != null && (
                            <Tag color="purple">Rerank {item.rerank_score.toFixed(3)}</Tag>
                          )}
                        </div>
                        <Paragraph className="kb-search-result-content">{item.content}</Paragraph>
                      </div>
                    ))}
                  </div>
                )}
              </Card>
            </>
          )}
        </div>
      </div>

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
    </AppLayout>
  );
}

export default function KnowledgeBase() {
  return (
    <RequireAuth>
      <KnowledgePage />
    </RequireAuth>
  );
}
