/**
 * 切片结果页 — 左文档预览 + 右切片列表，支持编辑切片。
 */
import { useCallback, useEffect, useMemo, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import {
  Alert,
  Button,
  Card,
  Empty,
  Input,
  Modal,
  Segmented,
  Spin,
  message,
} from "antd";
import { ArrowLeftOutlined, EditOutlined, SearchOutlined, SyncOutlined } from "@ant-design/icons";
import AppLayout from "../../components/layout/AppLayout";
import {
  fetchDocumentChunks,
  fetchDocumentContent,
  reembedDocument,
  updateDocumentChunk,
} from "../../api/knowledge";
import { formatDate, formatSize } from "./utils";
import "../../styles/knowledge.css";

const { TextArea } = Input;

export default function KnowledgeChunksPage() {
  const { kbId, docId } = useParams();
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [document, setDocument] = useState(null);
  const [content, setContent] = useState("");
  const [chunks, setChunks] = useState([]);
  const [viewMode, setViewMode] = useState("full");
  const [keyword, setKeyword] = useState("");
  const [editOpen, setEditOpen] = useState(false);
  const [editingChunk, setEditingChunk] = useState(null);
  const [editContent, setEditContent] = useState("");
  const [saving, setSaving] = useState(false);
  const [reembedding, setReembedding] = useState(false);

  const loadData = useCallback(async () => {
    setLoading(true);
    try {
      const [contentData, chunkList] = await Promise.all([
        fetchDocumentContent(kbId, docId),
        fetchDocumentChunks(kbId, docId),
      ]);
      setDocument(contentData.document);
      setContent(contentData.content || "");
      setChunks(chunkList);
    } catch (error) {
      message.error(error instanceof Error ? error.message : "加载失败");
      navigate(`/knowledge/${kbId}/files`, { replace: true });
    } finally {
      setLoading(false);
    }
  }, [kbId, docId, navigate]);

  useEffect(() => {
    void loadData();
  }, [loadData]);

  const filteredChunks = useMemo(() => {
    if (!keyword.trim()) {
      return chunks;
    }
    const q = keyword.trim().toLowerCase();
    return chunks.filter((item) => item.content?.toLowerCase().includes(q));
  }, [chunks, keyword]);

  const needsReembedding = document?.status === "needs_reembedding";

  function openEditModal(chunk) {
    setEditingChunk(chunk);
    setEditContent(chunk.content || "");
    setEditOpen(true);
  }

  async function handleSaveChunk() {
    if (!editingChunk?.id) {
      return;
    }
    if (!editContent.trim()) {
      message.warning("切片内容不能为空");
      return;
    }
    setSaving(true);
    try {
      const result = await updateDocumentChunk(kbId, docId, editingChunk.id, editContent.trim());
      setChunks((prev) =>
        prev.map((item) =>
          item.id === editingChunk.id ? { ...item, content: editContent.trim() } : item
        )
      );
      setDocument(result.document);
      setEditOpen(false);
      setEditingChunk(null);
      message.success("切片已更新，请重新向量化后用于检索");
    } catch (error) {
      message.error(error instanceof Error ? error.message : "保存失败");
    } finally {
      setSaving(false);
    }
  }

  async function handleReembed() {
    setReembedding(true);
    try {
      const doc = await reembedDocument(kbId, docId);
      setDocument(doc);
      message.success("向量化完成，文档已恢复就绪状态");
    } catch (error) {
      message.error(error instanceof Error ? error.message : "向量化失败");
      await loadData();
    } finally {
      setReembedding(false);
    }
  }

  if (loading) {
    return (
      <AppLayout title="切片结果">
        <div className="kb-page">
          <div className="kb-loading">
            <Spin tip="加载切片..." />
          </div>
        </div>
      </AppLayout>
    );
  }

  return (
    <AppLayout title="切片结果">
      <div className="kb-page kb-chunks-page">
        <Button
          type="link"
          icon={<ArrowLeftOutlined />}
          onClick={() => navigate(`/knowledge/${kbId}/files`)}
          style={{ padding: 0, width: "fit-content" }}
        >
          返回文件列表
        </Button>

        {needsReembedding && (
          <Alert
            type="warning"
            showIcon
            message="切片内容已变更，向量数据未同步"
            description="当前文档处于「待重新向量化」状态，检索不会使用最新切片内容。请执行重新向量化后再用于问答。"
            action={
              <Button
                size="small"
                type="primary"
                icon={<SyncOutlined />}
                loading={reembedding}
                onClick={handleReembed}
              >
                重新向量化
              </Button>
            }
          />
        )}

        <div className="kb-chunks-layout">
          <div className="kb-chunks-preview">
            <Card className="gov-page-card kb-chunks-preview-card" bordered={false}>
              <div className="kb-chunks-preview-header">
                <h1 className="kb-chunks-preview-title">
                  {document?.original_filename || "文档预览"}
                </h1>
                <div className="kb-chunks-preview-meta">
                  大小: {formatSize(document?.file_size)} · 上传时间:{" "}
                  {formatDate(document?.created_at)}
                </div>
              </div>
              <div className="kb-chunks-preview-body">
                {content || "无法预览文档内容"}
              </div>
            </Card>
          </div>

          <div className="kb-chunks-list-panel">
            <Card className="gov-page-card kb-chunks-list-card" bordered={false}>
              <div className="kb-chunks-list-header">
                <h2>切片结果</h2>
                <p>查看或编辑用于嵌入和召回的切片段落</p>
              </div>

              <div className="kb-chunks-toolbar">
                <Segmented
                  options={[
                    { label: "全文", value: "full" },
                    { label: "省略", value: "ellipsis" },
                  ]}
                  value={viewMode}
                  onChange={setViewMode}
                />
                <Input
                  prefix={<SearchOutlined />}
                  placeholder="搜索切片内容"
                  value={keyword}
                  onChange={(e) => setKeyword(e.target.value)}
                  style={{ width: 200 }}
                  allowClear
                />
                <span className="kb-chunks-meta-text">共 {filteredChunks.length} 个切片</span>
              </div>

              <div className="kb-chunks-container">
                {filteredChunks.length === 0 ? (
                  <Empty description="暂无切片" />
                ) : (
                  filteredChunks.map((chunk) => (
                    <div key={chunk.id ?? chunk.chunk_index} className="kb-chunk-card">
                      <div className="kb-chunk-card-header">
                        <span className="kb-chunk-card-label">
                          片段 #{Number(chunk.chunk_index || 0) + 1}
                        </span>
                        <Button
                          type="link"
                          size="small"
                          icon={<EditOutlined />}
                          onClick={() => openEditModal(chunk)}
                        >
                          编辑
                        </Button>
                      </div>
                      <p
                        className={`kb-chunk-card-content ${
                          viewMode === "ellipsis" ? "truncated" : ""
                        }`}
                      >
                        {chunk.content}
                      </p>
                    </div>
                  ))
                )}
              </div>
            </Card>
          </div>
        </div>

        <Modal
          title={`编辑切片 #${Number(editingChunk?.chunk_index || 0) + 1}`}
          open={editOpen}
          onCancel={() => {
            setEditOpen(false);
            setEditingChunk(null);
          }}
          onOk={handleSaveChunk}
          confirmLoading={saving}
          okText="确认"
          cancelText="取消"
          width={720}
          destroyOnClose
        >
          <div className="kb-chunk-edit-field">
            <div className="kb-chunk-edit-label">切片内容</div>
            <TextArea
              rows={14}
              value={editContent}
              onChange={(e) => setEditContent(e.target.value)}
              placeholder="请输入切片内容"
            />
          </div>
        </Modal>
      </div>
    </AppLayout>
  );
}
