/**
 * 路由守卫：要求已登录（localStorage 中存在 token）。
 *
 * 用法:
 * - 包裹需登录的页面，如 `/chat`
 * - 未登录时重定向到 `/login`
 */
import { Navigate } from "react-router-dom";
import { isAuthenticated } from "../api/auth";

export default function RequireAuth({ children }) {
  if (!isAuthenticated()) {
    return <Navigate to="/login" replace />;
  }
  return children;
}
