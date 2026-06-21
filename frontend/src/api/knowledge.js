/**
 * 知识库 REST API。
 */
import { apiFetch, apiUpload } from "./client";

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
