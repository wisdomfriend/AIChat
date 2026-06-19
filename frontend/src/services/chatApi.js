/**
 * 聊天相关 REST API 封装。
 */
import { getToken } from "../api/auth";
import { apiFetch, apiUpload, buildUrl } from "../api/client";

export const MAX_MESSAGE_BYTES = 64 * 1024;

export function formatBytes(bytes) {
  if (bytes < 1024) {
    return `${bytes} B`;
  }
  if (bytes < 1024 * 1024) {
    return `${(bytes / 1024).toFixed(1)} KB`;
  }
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export function getTextSizeInBytes(text) {
  return new Blob([text]).size;
}

const IMAGE_EXT = /\.(png|jpe?g|gif|webp|bmp|svg)$/i;

export function isImageFile(name) {
  return IMAGE_EXT.test(String(name || ""));
}

export async function fetchSessions() {
  const data = await apiFetch("/api/sessions");
  return data.sessions || [];
}

export async function fetchSessionMessages(sessionId) {
  const data = await apiFetch(`/api/sessions/${sessionId}/messages`);
  return data.messages || [];
}

export async function fetchLlmProviders() {
  const data = await apiFetch("/api/llm/providers");
  return {
    providers: data.providers || [],
    defaultProvider: data.default || "",
  };
}

export async function uploadChatFile(file) {
  const formData = new FormData();
  formData.append("file", file);
  return apiUpload("/api/files", formData);
}

export async function uploadChatFiles(files) {
  const uploaded = [];

  for (const item of files) {
    if (item.uploaded && item.server_id) {
      uploaded.push({
        ...item,
        id: item.server_id,
      });
      continue;
    }
    if (!item.file) {
      continue;
    }
    const result = await uploadChatFile(item.file);
    uploaded.push({
      id: result.file_id,
      server_id: result.file_id,
      original_filename: result.filename || item.original_filename,
      file_size: item.file_size ?? result.file_size,
      is_image: item.is_image ?? isImageFile(result.filename),
      uploaded: true,
    });
  }

  return uploaded;
}

export async function fetchImageBlobUrl(fileId) {
  const token = getToken();
  const response = await fetch(buildUrl(`/api/files/${fileId}/image`), {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  });

  if (!response.ok) {
    throw new Error("加载图片失败");
  }

  const blob = await response.blob();
  return URL.createObjectURL(blob);
}
