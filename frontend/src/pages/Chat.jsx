/**
 * 聊天主页面（阶段 3）。
 *
 * 职责总览：
 * 1) 初始化
 *    - 加载用户、会话列表、LLM 提供商
 * 2) 会话切换
 *    - 选择历史会话 / 新对话
 * 3) 发送消息
 *    - 文件上传 → POST /api/chat SSE
 */
import { useCallback, useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Spin, message } from "antd";
import RequireAuth from "../components/RequireAuth";
import SessionSidebar from "../components/chat/SessionSidebar";
import MessageList from "../components/chat/MessageList";
import ChatComposer from "../components/chat/ChatComposer";
import { clearAuth } from "../api/auth";
import { apiFetch } from "../api/client";
import {
  fetchLlmProviders,
  fetchSessionMessages,
  fetchSessions,
  uploadChatFiles,
} from "../services/chatApi";
import { createChatStreamController, streamChatMessage } from "../hooks/useChatStream";
import { useChatStore } from "../stores/chatStore";
import "../styles/chat.css";

function ChatPage() {
  const navigate = useNavigate();
  const [bootLoading, setBootLoading] = useState(true);
  const streamRef = useRef(null);

  const user = useChatStore((s) => s.user);
  const sessionId = useChatStore((s) => s.sessionId);
  const sessions = useChatStore((s) => s.sessions);
  const messages = useChatStore((s) => s.messages);
  const streamText = useChatStore((s) => s.streamText);
  const waitingReply = useChatStore((s) => s.waitingReply);
  const sending = useChatStore((s) => s.sending);
  const statusText = useChatStore((s) => s.statusText);
  const llmProviders = useChatStore((s) => s.llmProviders);
  const llmProvider = useChatStore((s) => s.llmProvider);
  const agentMode = useChatStore((s) => s.agentMode);
  const selectedFiles = useChatStore((s) => s.selectedFiles);
  const isNewChatDraft = useChatStore((s) => s.isNewChatDraft);

  const reloadSessions = useCallback(async () => {
    const list = await fetchSessions();
    useChatStore.setState({ sessions: list });
    return list;
  }, []);

  const loadMessages = useCallback(async (sid) => {
    const list = await fetchSessionMessages(sid);
    useChatStore.setState({
      messages: list.map((m) => ({
        ...m,
        id: m.id ?? `${m.role}-${m.created_at}`,
      })),
      sessionId: sid,
      isNewChatDraft: false,
    });
  }, []);

  useEffect(() => {
    let cancelled = false;

    async function boot() {
      try {
        const [meData, providerData, sessionList] = await Promise.all([
          apiFetch("/api/auth/me"),
          fetchLlmProviders(),
          fetchSessions(),
        ]);
        if (cancelled) {
          return;
        }

        useChatStore.setState({
          user: meData.user,
          llmProviders: providerData.providers,
          defaultProvider: providerData.defaultProvider,
          llmProvider: providerData.defaultProvider,
          sessions: sessionList,
          isNewChatDraft: sessionList.length === 0,
        });

        const withMessages = sessionList.find((s) => (s.message_count || 0) > 0) || sessionList[0];
        if (withMessages) {
          await loadMessages(withMessages.id);
        }
      } catch (error) {
        if (!cancelled) {
          message.error(error instanceof Error ? error.message : "加载失败");
          navigate("/login", { replace: true });
        }
      } finally {
        if (!cancelled) {
          setBootLoading(false);
        }
      }
    }

    void boot();
    return () => {
      cancelled = true;
      streamRef.current?.abort();
    };
  }, [loadMessages, navigate]);

  function handleLogout() {
    clearAuth();
    navigate("/login", { replace: true });
  }

  function handleNewChat() {
    if (waitingReply || sending) {
      streamRef.current?.abort();
    }
    useChatStore.getState().resetChat();
  }

  async function handleSelectSession(sid) {
    if (sid === sessionId) {
      return;
    }
    if (waitingReply || sending) {
      streamRef.current?.abort();
    }
    useChatStore.setState({
      streamText: "",
      waitingReply: false,
      sending: false,
      statusText: "",
      selectedFiles: [],
    });
    try {
      await loadMessages(sid);
    } catch (error) {
      message.error(error instanceof Error ? error.message : "加载会话失败");
    }
  }

  async function handleSend(text) {
    const state = useChatStore.getState();
    if (state.sending || state.waitingReply) {
      return;
    }

    const pendingFiles = [...state.selectedFiles];

    useChatStore.setState({
      sending: true,
      waitingReply: true,
      streamText: "",
      streamUsage: null,
      statusText: "正在思考...",
      activeStreamSessionId: state.sessionId,
      selectedFiles: [],
    });

    try {
      const uploadedFiles = await uploadChatFiles(pendingFiles);
      const fileIds = uploadedFiles.map((f) => f.server_id || f.id).filter(Boolean);
      const displayFiles = uploadedFiles.map((f) => ({
        id: f.server_id || f.id,
        filename: f.original_filename,
        file_size: f.file_size,
        is_image: f.is_image,
      }));

      useChatStore.setState({
        messages: [
          ...state.messages,
          {
            id: `user-${Date.now()}`,
            role: "user",
            content: text,
            created_at: new Date().toISOString(),
            files: displayFiles,
          },
        ],
      });
      streamRef.current?.abort();
      streamRef.current = createChatStreamController();

      await streamChatMessage({
        message: text,
        sessionId: useChatStore.getState().sessionId,
        fileIds,
        llmProvider: useChatStore.getState().llmProvider,
        agentMode: useChatStore.getState().agentMode,
        storeApi: useChatStore,
        signal: streamRef.current.signal,
        onReloadSessions: () => {
          void reloadSessions();
        },
      });

      await reloadSessions();
    } catch (error) {
      if (error?.name !== "AbortError") {
        message.error(error instanceof Error ? error.message : "发送失败");
        useChatStore.setState({ statusText: "请求失败" });
      }
    } finally {
      useChatStore.setState({ sending: false, waitingReply: false, activeStreamSessionId: null });
    }
  }

  function handleStop() {
    streamRef.current?.abort();
    useChatStore.setState({ sending: false, waitingReply: false });
  }

  if (bootLoading) {
    return (
      <div className="chat-loading">
        <Spin tip="加载聊天..." />
      </div>
    );
  }

  return (
    <div className="chat-app">
      <SessionSidebar
        user={user}
        sessions={sessions}
        sessionId={sessionId}
        onNewChat={handleNewChat}
        onSelectSession={handleSelectSession}
        onLogout={handleLogout}
      />

      <main className="chat-main">
        <MessageList
          messages={messages}
          streamText={streamText}
          waitingReply={waitingReply}
          showWelcome={isNewChatDraft || !sessionId}
        />

        <ChatComposer
          disabled={bootLoading}
          sending={sending}
          waitingReply={waitingReply}
          llmProviders={llmProviders}
          llmProvider={llmProvider}
          agentMode={agentMode}
          selectedFiles={selectedFiles}
          statusText={statusText}
          onChangeProvider={(v) => useChatStore.setState({ llmProvider: v })}
          onChangeAgentMode={(v) => useChatStore.setState({ agentMode: v })}
          onChangeFiles={(files) => useChatStore.setState({ selectedFiles: files })}
          onSend={handleSend}
          onStop={handleStop}
        />
      </main>
    </div>
  );
}

export default function Chat() {
  return (
    <RequireAuth>
      <ChatPage />
    </RequireAuth>
  );
}
