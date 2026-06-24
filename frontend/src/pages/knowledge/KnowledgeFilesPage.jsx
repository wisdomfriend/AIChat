/**
 * 文件列表页 — 上传、管理文档，点击文件名查看切片。
 */
import { useCallback, useEffect, useMemo, useState } from "react";
import { useNavigate, useOutletContext, useParams } from "react-router-dom";
import {
  Button,
  Card,
  Input,
  Popconfirm,
  Select,
  Spin,
  Table,
  Tag,
  Tooltip,
  Upload,
  message,
} from "antd";
import {
  CheckCircleOutlined,
  DeleteOutlined,
  DownloadOutlined,
  EyeOutlined,
  InboxOutlined,
  ReloadOutlined,
  SearchOutlined,
  StopOutlined,
  SyncOutlined,
  UploadOutlined,
} from "@ant-design/icons";
import {
  batchUpdateDocuments,
  deleteKnowledgeBase,
  deleteKnowledgeDocument,
  downloadKnowledgeDocument,
  fetchDocuments,
  fetchKnowledgeSupported,
  reembedDocument,
  uploadKnowledgeDocument,
} from "../../api/knowledge";
import { STATUS_MAP, formatDate, formatSize, getFileTypeMeta } from "./utils";

const { Dragger } = Upload;

export default function KnowledgeFilesPage() {
  const { kbId } = useParams();
  const navigate = useNavigate();
  const { refreshKb } = useOutletContext();

  const [documents, setDocuments] = useState([]);
  const [docsLoading, setDocsLoading] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [bulkLoading, setBulkLoading] = useState(false);
  const [reembeddingId, setReembeddingId] = useState(null);
  const [supported, setSupported] = useState({ extensions: [], max_size_mb: 100 });
  const [keyword, setKeyword] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");
  const [enabledFilter, setEnabledFilter] = useState("all");
  const [selectedRowKeys, setSelectedRowKeys] = useState([]);

  const loadDocuments = useCallback(async () => {
    if (!kbId) {
      return;
    }
    setDocsLoading(true);
    try {
      const list = await fetchDocuments(kbId);
      setDocuments(list);
      setSelectedRowKeys([]);
    } finally {
      setDocsLoading(false);
    }
  }, [kbId]);

  useEffect(() => {
    let cancelled = false;
    async function boot() {
      try {
        const info = await fetchKnowledgeSupported();
        if (!cancelled) {
          setSupported(info);
        }
      } catch {
        /* ignore */
      }
    }
    void boot();
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    void loadDocuments();
  }, [loadDocuments]);

  const filteredDocuments = useMemo(() => {
    let list = documents;
    if (statusFilter !== "all") {
      list = list.filter((doc) => doc.status === statusFilter);
    }
    if (enabledFilter === "enabled") {
      list = list.filter((doc) => doc.is_enabled !== false);
    } else if (enabledFilter === "disabled") {
      list = list.filter((doc) => doc.is_enabled === false);
    }
    if (keyword.trim()) {
      const q = keyword.trim().toLowerCase();
      list = list.filter((doc) => doc.original_filename?.toLowerCase().includes(q));
    }
    return list;
  }, [documents, enabledFilter, keyword, statusFilter]);

  async function handleUpload(file) {
    setUploading(true);
    try {
      await uploadKnowledgeDocument(kbId, file);
      message.success(`${file.name} 上传成功，正在解析入库`);
      await Promise.all([loadDocuments(), refreshKb?.()]);
    } catch (error) {
      message.error(error instanceof Error ? error.message : "上传失败");
    } finally {
      setUploading(false);
    }
    return false;
  }

  async function handleBulkDelete() {
    if (!selectedRowKeys.length) {
      return;
    }
    setBulkLoading(true);
    try {
      await Promise.all(selectedRowKeys.map((id) => deleteKnowledgeDocument(kbId, id)));
      message.success(`已删除 ${selectedRowKeys.length} 个文档`);
      await Promise.all([loadDocuments(), refreshKb?.()]);
    } catch (error) {
      message.error(error instanceof Error ? error.message : "批量删除失败");
    } finally {
      setBulkLoading(false);
    }
  }

  async function handleBulkEnabled(isEnabled) {
    if (!selectedRowKeys.length) {
      return;
    }
    setBulkLoading(true);
    try {
      const data = await batchUpdateDocuments(kbId, selectedRowKeys, isEnabled);
      message.success(`已${isEnabled ? "启用" : "禁用"} ${data.updated || selectedRowKeys.length} 个文档`);
      await loadDocuments();
    } catch (error) {
      message.error(error instanceof Error ? error.message : "批量操作失败");
    } finally {
      setBulkLoading(false);
    }
  }

  async function handleDeleteKb() {
    try {
      await deleteKnowledgeBase(kbId);
      message.success("知识库已删除");
      navigate("/knowledge");
    } catch (error) {
      message.error(error instanceof Error ? error.message : "删除失败");
    }
  }

  async function handleDownload(record) {
    try {
      await downloadKnowledgeDocument(kbId, record.id, record.original_filename);
    } catch (error) {
      message.error(error instanceof Error ? error.message : "下载失败");
    }
  }

  async function handleReembed(record) {
    setReembeddingId(record.id);
    try {
      await reembedDocument(kbId, record.id);
      message.success(`${record.original_filename} 向量化完成`);
      await loadDocuments();
    } catch (error) {
      message.error(error instanceof Error ? error.message : "向量化失败");
    } finally {
      setReembeddingId(null);
    }
  }

  function canViewChunks(record) {
    return record.status === "ready" || record.status === "needs_reembedding";
  }

  function openChunks(record) {
    if (canViewChunks(record)) {
      navigate(`/knowledge/${kbId}/chunks/${record.id}`);
      return;
    }
    if (record.status === "processing" || record.status === "pending") {
      message.info("文档正在处理中，请稍后查看");
      return;
    }
    message.warning(record.error_message || "文档处理失败，无法查看切片");
  }

  const acceptTypes = supported.extensions
    ?.map((ext) => `.${ext.replace(/^\./, "")}`)
    .join(",");

  const columns = [
    {
      title: "名称",
      dataIndex: "original_filename",
      key: "original_filename",
      ellipsis: true,
      sorter: (a, b) => (a.original_filename || "").localeCompare(b.original_filename || ""),
      render: (name, record) => {
        const meta = getFileTypeMeta(name, record.file_extension);
        const clickable = canViewChunks(record);
        return (
          <div className="kb-file-name-cell">
            <div className="kb-file-type-icon" style={{ background: meta.color }}>
              {meta.label}
            </div>
            <Tooltip title={name}>
              <span
                className={`kb-file-name-text kb-file-link ${clickable ? "" : "disabled"}`}
                onClick={() => openChunks(record)}
              >
                {name}
              </span>
            </Tooltip>
          </div>
        );
      },
    },
    {
      title: "上传时间",
      dataIndex: "created_at",
      key: "created_at",
      width: 150,
      sorter: (a, b) => new Date(a.created_at || 0) - new Date(b.created_at || 0),
      render: (value) => formatDate(value),
    },
    {
      title: "解析状态",
      dataIndex: "status",
      key: "status",
      width: 100,
      render: (status, record) => {
        const meta = STATUS_MAP[status] || STATUS_MAP.pending;
        return (
          <div className="kb-files-status-cell">
            {(status === "processing" || status === "pending") && <Spin size="small" />}
            <Tooltip title={record.error_message || undefined}>
              <Tag color={meta.color}>{meta.text}</Tag>
            </Tooltip>
          </div>
        );
      },
    },
    {
      title: "启用",
      dataIndex: "is_enabled",
      key: "is_enabled",
      width: 72,
      align: "center",
      render: (enabled) =>
        enabled === false ? (
          <Tag color="default">已禁用</Tag>
        ) : (
          <Tag color="success">已启用</Tag>
        ),
    },
    {
      title: "切片数",
      dataIndex: "chunk_count",
      key: "chunk_count",
      width: 72,
      align: "center",
      sorter: (a, b) => (a.chunk_count || 0) - (b.chunk_count || 0),
      render: (count, record) =>
        record.status === "ready" || record.status === "needs_reembedding" ? count || 0 : "-",
    },
    {
      title: "大小",
      dataIndex: "file_size",
      key: "file_size",
      width: 80,
      sorter: (a, b) => (a.file_size || 0) - (b.file_size || 0),
      render: (size) => formatSize(size),
    },
    {
      title: "操作",
      key: "actions",
      width: 210,
      fixed: "right",
      render: (_, record) => (
        <div className="kb-files-actions">
          <Button
            type="link"
            size="small"
            icon={<EyeOutlined />}
            disabled={!canViewChunks(record)}
            onClick={() => openChunks(record)}
          >
            查看切片
          </Button>
          {record.status === "needs_reembedding" && (
            <Button
              type="link"
              size="small"
              icon={<SyncOutlined />}
              loading={reembeddingId === record.id}
              onClick={() => handleReembed(record)}
            >
              重新向量化
            </Button>
          )}
          <Button
            type="link"
            size="small"
            icon={<DownloadOutlined />}
            onClick={() => handleDownload(record)}
          >
            下载
          </Button>
        </div>
      ),
    },
  ];

  const readyCount = documents.filter((doc) => doc.status === "ready").length;
  const reembedCount = documents.filter((doc) => doc.status === "needs_reembedding").length;
  const processingCount = documents.filter(
    (doc) => doc.status === "processing" || doc.status === "pending"
  ).length;

  return (
    <div className="kb-detail-content kb-files-page">
      <Card className="gov-page-card kb-files-header-card" bordered={false}>
        <div className="kb-files-header-row">
          <div>
            <h1 className="kb-page-title">文件列表</h1>
            <p className="kb-page-desc">解析成功后方可用于知识检索与问答，点击文件名可查看切片详情。</p>
          </div>
          <div className="kb-files-header-actions">
            <Upload
              className="kb-upload-trigger"
              multiple
              showUploadList={false}
              accept={acceptTypes}
              beforeUpload={handleUpload}
              disabled={uploading}
            >
              <Button type="primary" icon={<UploadOutlined />} loading={uploading}>
                上传文件
              </Button>
            </Upload>
            <Button icon={<ReloadOutlined />} onClick={() => loadDocuments()} loading={docsLoading}>
              刷新
            </Button>
            <Popconfirm title="删除后不可恢复，确定继续？" onConfirm={handleDeleteKb}>
              <Button danger icon={<DeleteOutlined />}>
                删除知识库
              </Button>
            </Popconfirm>
          </div>
        </div>
      </Card>

      <Card className="gov-page-card kb-files-table-card" bordered={false}>
        <div className="kb-files-table-toolbar">
          <div className="kb-files-table-toolbar-left">
            <Input
              prefix={<SearchOutlined />}
              placeholder="搜索文件名"
              value={keyword}
              onChange={(e) => setKeyword(e.target.value)}
              style={{ width: 200 }}
              size="small"
              allowClear
            />
            <Select
              value={statusFilter}
              onChange={setStatusFilter}
              style={{ width: 110 }}
              size="small"
              options={[
                { value: "all", label: "全部状态" },
                { value: "ready", label: "已就绪" },
                { value: "processing", label: "处理中" },
                { value: "pending", label: "等待中" },
                { value: "failed", label: "失败" },
                { value: "needs_reembedding", label: "待重新向量化" },
              ]}
            />
            <Select
              value={enabledFilter}
              onChange={setEnabledFilter}
              style={{ width: 110 }}
              size="small"
              options={[
                { value: "all", label: "全部启用" },
                { value: "enabled", label: "已启用" },
                { value: "disabled", label: "已禁用" },
              ]}
            />
          </div>
        </div>

        {filteredDocuments.length === 0 && !docsLoading && documents.length === 0 && (
          <Dragger
            className="kb-files-empty-upload"
            multiple
            showUploadList={false}
            accept={acceptTypes}
            beforeUpload={handleUpload}
            disabled={uploading}
          >
            <p className="ant-upload-drag-icon">
              <InboxOutlined />
            </p>
            <p className="ant-upload-text">点击或拖拽文件到此处上传</p>
            <p className="ant-upload-hint">
              支持 {supported.extensions?.join("、") || "txt、md、doc、docx"}，单文件最大{" "}
              {supported.max_size_mb || 100}MB
            </p>
          </Dragger>
        )}

        {selectedRowKeys.length > 0 && (
          <div className="kb-files-bulk-bar">
            <span>已选择 {selectedRowKeys.length} 项</span>
            <Button
              size="small"
              icon={<CheckCircleOutlined />}
              loading={bulkLoading}
              onClick={() => handleBulkEnabled(true)}
            >
              批量启用
            </Button>
            <Button
              size="small"
              icon={<StopOutlined />}
              loading={bulkLoading}
              onClick={() => handleBulkEnabled(false)}
            >
              批量禁用
            </Button>
            <Popconfirm
              title={`确定删除选中的 ${selectedRowKeys.length} 个文档？`}
              onConfirm={handleBulkDelete}
            >
              <Button size="small" danger icon={<DeleteOutlined />} loading={bulkLoading}>
                批量删除
              </Button>
            </Popconfirm>
            <Button size="small" type="link" onClick={() => setSelectedRowKeys([])}>
              取消选择
            </Button>
          </div>
        )}

        <Table
          className="kb-files-table"
          rowKey="id"
          size="small"
          loading={docsLoading}
          columns={columns}
          dataSource={filteredDocuments}
          rowSelection={{
            selectedRowKeys,
            onChange: setSelectedRowKeys,
          }}
          scroll={{ x: 980 }}
          pagination={{
            pageSize: 10,
            showSizeChanger: true,
            showTotal: (total) => `共 ${total} 个文件`,
            pageSizeOptions: ["10", "20", "50"],
            size: "small",
          }}
          locale={{ emptyText: documents.length === 0 ? " " : "没有匹配的文档" }}
        />

        <div className="kb-files-footer">
          <span>
            共 {documents.length} 个文件，{readyCount} 个已就绪
            {reembedCount > 0 ? `，${reembedCount} 个待重新向量化` : ""}
            {processingCount > 0 ? `，${processingCount} 个处理中` : ""}
          </span>
          <span>
            支持 {supported.extensions?.join("、") || "txt、md、doc、docx"}，单文件最大{" "}
            {supported.max_size_mb || 100}MB
          </span>
        </div>
      </Card>
    </div>
  );
}
