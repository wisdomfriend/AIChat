import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { isAuthenticated } from "./api/auth";
import Admin from "./pages/Admin";
import BgPreview from "./pages/BgPreview";
import Chat from "./pages/Chat";
import Dashboard from "./pages/Dashboard";
import KnowledgeBase from "./pages/KnowledgeBase";
import Login from "./pages/Login";
import Register from "./pages/Register";

function RootRedirect() {
  return <Navigate to={isAuthenticated() ? "/chat" : "/login"} replace />;
}

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<RootRedirect />} />
        <Route path="/login" element={<Login />} />
        <Route path="/register" element={<Register />} />
        <Route path="/bg-preview" element={<BgPreview />} />
        <Route path="/chat" element={<Chat />} />
        <Route path="/knowledge/*" element={<KnowledgeBase />} />
        <Route path="/dashboard" element={<Dashboard />} />
        <Route path="/admin" element={<Admin />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  );
}
