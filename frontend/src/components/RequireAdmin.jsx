/**
 * 路由守卫：要求 admin 权限。
 */
import { Navigate } from "react-router-dom";
import { getStoredUser, isAuthenticated } from "../api/auth";

export default function RequireAdmin({ children }) {
  if (!isAuthenticated()) {
    return <Navigate to="/login" replace />;
  }

  const user = getStoredUser();
  if (!user?.is_admin) {
    return <Navigate to="/chat" replace />;
  }

  return children;
}
