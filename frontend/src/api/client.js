/**
 * HTTP 请求封装（JSON API）。
 *
 * 职责总览：
 * 1) 请求构建
 *    - buildUrl()   拼接 API 基址
 *    - apiFetch()   统一 fetch，自动附加 Bearer token
 * 2) 错误处理
 *    - 非 2xx 解析 `{ message | error }`
 *    - 401 时调用 clearAuth() 清除本地 token
 */
import { clearAuth, getToken } from "./auth";

const DEFAULT_API_BASE =
  import.meta.env.VITE_API_BASE_URL ||
  `${window.location.protocol}//${window.location.hostname}${window.location.port ? `:${window.location.port}` : ""}`;

function buildUrl(path) {
  if (path.startsWith("http")) {
    return path;
  }
  return `${DEFAULT_API_BASE}${path}`;
}

export { buildUrl };

export async function apiUpload(path, formData, token) {
  const headers = {};
  const authToken = token !== undefined ? token : getToken();
  if (authToken) {
    headers.Authorization = `Bearer ${authToken}`;
  }

  const response = await fetch(buildUrl(path), {
    method: "POST",
    headers,
    body: formData,
  });

  if (!response.ok) {
    const data = await response.json().catch(() => ({}));
    const message = data.message || data.error || `请求失败: ${response.status}`;
    if (response.status === 401) {
      clearAuth();
    }
    throw new Error(message);
  }

  return response.json();
}

export async function apiFetch(path, options = {}, token) {
  const headers = {
    "Content-Type": "application/json",
    ...(options.headers || {}),
  };

  const authToken = token !== undefined ? token : getToken();
  if (authToken) {
    headers.Authorization = `Bearer ${authToken}`;
  }

  const response = await fetch(buildUrl(path), {
    ...options,
    headers,
  });

  if (!response.ok) {
    const data = await response.json().catch(() => ({}));
    const message = data.message || data.error || `请求失败: ${response.status}`;
    if (response.status === 401) {
      clearAuth();
    }
    throw new Error(message);
  }

  if (response.status === 204) {
    return null;
  }

  return response.json();
}
