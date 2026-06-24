/**
 * 知识库 REST API。
 */
import { apiFetch, apiUpload, buildUrl } from "./client";
import { clearAuth, getToken } from "./auth";

export async function fetchKnowledgeBases() {
  const data = await apiFetch("/api/knowledge-bases");
  return data.knowledge_bases || [];
}

export async function createKnowledgeBase(payload) {
  const data = await apiFetch("/api/knowledge-bases", {
    method: "POST",
    body: JSON.stringify(payload),
  });
  return data.knowledge_base;
}

export async function updateKnowledgeBase(id, payload) {
  const data = await apiFetch(`/api/knowledge-bases/${id}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
  return data.knowledge_base;
}

export async function deleteKnowledgeBase(id) {
  return apiFetch(`/api/knowledge-bases/${id}`, { method: "DELETE" });
}

export async function fetchDocuments(kbId) {
  const data = await apiFetch(`/api/knowledge-bases/${kbId}/documents`);
  return data.documents || [];
}

export async function uploadKnowledgeDocument(kbId, file) {
  const formData = new FormData();
  formData.append("file", file);
  return apiUpload(`/api/knowledge-bases/${kbId}/documents`, formData);
}

export async function deleteKnowledgeDocument(kbId, docId) {
  return apiFetch(`/api/knowledge-bases/${kbId}/documents/${docId}`, {
    method: "DELETE",
  });
}

export async function batchUpdateDocuments(kbId, documentIds, isEnabled) {
  return apiFetch(`/api/knowledge-bases/${kbId}/documents/batch`, {
    method: "PATCH",
    body: JSON.stringify({ document_ids: documentIds, is_enabled: isEnabled }),
  });
}

export async function downloadKnowledgeDocument(kbId, docId, filename) {
  const token = getToken();
  const response = await fetch(buildUrl(`/api/knowledge-bases/${kbId}/documents/${docId}/download`), {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  });
  if (!response.ok) {
    const data = await response.json().catch(() => ({}));
    if (response.status === 401) {
      clearAuth();
    }
    throw new Error(data.error || data.message || "下载失败");
  }
  const blob = await response.blob();
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename || "document";
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

export async function searchKnowledgeBase(kbId, query, topK) {
  const data = await apiFetch(`/api/knowledge-bases/${kbId}/search`, {
    method: "POST",
    body: JSON.stringify({ query, top_k: topK }),
  });
  return data;
}

export async function fetchKnowledgeSupported() {
  return apiFetch("/api/knowledge/supported");
}

export async function fetchDocumentChunks(kbId, docId) {
  const data = await apiFetch(`/api/knowledge-bases/${kbId}/documents/${docId}/chunks`);
  return data.chunks || [];
}

export async function fetchDocumentContent(kbId, docId) {
  return apiFetch(`/api/knowledge-bases/${kbId}/documents/${docId}/content`);
}

export async function updateDocumentChunk(kbId, docId, chunkId, content) {
  return apiFetch(`/api/knowledge-bases/${kbId}/documents/${docId}/chunks/${chunkId}`, {
    method: "PATCH",
    body: JSON.stringify({ content }),
  });
}

export async function reembedDocument(kbId, docId) {
  const data = await apiFetch(`/api/knowledge-bases/${kbId}/documents/${docId}/reembed`, {
    method: "POST",
  });
  return data.document;
}
