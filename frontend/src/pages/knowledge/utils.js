export const STATUS_MAP = {
  ready: { color: "success", text: "已就绪" },
  processing: { color: "processing", text: "处理中" },
  pending: { color: "default", text: "等待中" },
  failed: { color: "error", text: "失败" },
  needs_reembedding: { color: "warning", text: "待重新向量化" },
};

export function formatSize(bytes) {
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

export function formatDate(iso) {
  if (!iso) {
    return "-";
  }
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) {
    return "-";
  }
  return date.toLocaleString("zh-CN", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function kbInitial(name) {
  const text = (name || "K").trim();
  return text.charAt(0).toUpperCase();
}

const FILE_ICON_MAP = {
  pdf: { color: "#ff4d4f", label: "PDF" },
  doc: { color: "#1677ff", label: "DOC" },
  docx: { color: "#1677ff", label: "DOC" },
  txt: { color: "#64748b", label: "TXT" },
  md: { color: "#52c41a", label: "MD" },
  xlsx: { color: "#13c2c2", label: "XLS" },
  xls: { color: "#13c2c2", label: "XLS" },
  ppt: { color: "#fa8c16", label: "PPT" },
  pptx: { color: "#fa8c16", label: "PPT" },
};

export function getFileTypeMeta(filename, extension) {
  const ext = (extension || filename?.split(".").pop() || "")
    .replace(/^\./, "")
    .toLowerCase();
  return FILE_ICON_MAP[ext] || { color: "#94a3b8", label: ext.slice(0, 3).toUpperCase() || "FILE" };
}
