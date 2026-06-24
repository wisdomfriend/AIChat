/**
 * 知识库模块入口 — 嵌套路由。
 */
import { Navigate, Route, Routes } from "react-router-dom";
import RequireAuth from "../components/RequireAuth";
import KnowledgeListPage from "./knowledge/KnowledgeListPage";
import KnowledgeDetailLayout from "./knowledge/KnowledgeDetailLayout";
import KnowledgeFilesPage from "./knowledge/KnowledgeFilesPage";
import KnowledgeTestingPage from "./knowledge/KnowledgeTestingPage";
import KnowledgeChunksPage from "./knowledge/KnowledgeChunksPage";

export default function KnowledgeBase() {
  return (
    <RequireAuth>
      <Routes>
        <Route index element={<KnowledgeListPage />} />
        <Route path=":kbId/chunks/:docId" element={<KnowledgeChunksPage />} />
        <Route path=":kbId/*" element={<KnowledgeDetailLayout />}>
          <Route index element={<Navigate to="files" replace />} />
          <Route path="files" element={<KnowledgeFilesPage />} />
          <Route path="testing" element={<KnowledgeTestingPage />} />
        </Route>
      </Routes>
    </RequireAuth>
  );
}
