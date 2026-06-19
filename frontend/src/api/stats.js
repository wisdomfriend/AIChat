/**
 * Token 统计 API。
 */
import { apiFetch } from "./client";

export async function fetchUserStats() {
  return apiFetch("/api/stats/user");
}

export async function fetchAdminStats() {
  return apiFetch("/api/stats/admin");
}
