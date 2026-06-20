/**
 * Bearer Token 本地存储（前端认证状态）。
 *
 * 职责总览：
 * 1) 读取
 *    - getToken()       获取 token
 *    - getStoredUser()  获取缓存的用户信息
 *    - isAuthenticated() 是否已登录
 * 2) 写入/清除
 *    - setAuth()   登录成功后保存 token 与 user
 *    - clearAuth() 登出或 401 时清除
 */
const TOKEN_KEY = "auth_token";
const USER_KEY = "auth_user";

export function getToken() {
  return localStorage.getItem(TOKEN_KEY) || "";
}

export function getStoredUser() {
  const raw = localStorage.getItem(USER_KEY);
  if (!raw) {
    return null;
  }
  try {
    return JSON.parse(raw);
  } catch {
    return null;
  }
}

export function setAuth(token, user) {
  localStorage.setItem(TOKEN_KEY, token);
  localStorage.setItem(USER_KEY, JSON.stringify(user));
}

export function clearAuth() {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(USER_KEY);
}

export function isAuthenticated() {
  return Boolean(getToken());
}
