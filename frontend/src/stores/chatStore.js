/**
 * 聊天页 Zustand 状态（阶段 3）。
 *
 * 职责总览：
 * 1) 会话
 *    - sessionId / sessions / isNewChatDraft
 * 2) 消息与流式
 *    - messages / streamText / streamUsage / waitingReply / sending
 * 3) 模型与 Agent
 *    - llmProviders / llmProvider / agentMode
 * 4) 文件与状态栏
 *    - selectedFiles / statusText
 */
import { create } from "zustand";

export const useChatStore = create((set) => ({
  user: null,
  sessionId: null,
  sessions: [],
  messages: [],
  streamText: "",
  streamUsage: null,
  sending: false,
  waitingReply: false,
  statusText: "",
  llmProviders: [],
  llmProvider: "",
  defaultProvider: "",
  agentMode: "normal",
  selectedFiles: [],
  isNewChatDraft: false,
  activeStreamSessionId: null,

  resetStream: () =>
    set({
      streamText: "",
      streamUsage: null,
      waitingReply: false,
      sending: false,
      activeStreamSessionId: null,
    }),

  resetChat: () =>
    set({
      sessionId: null,
      messages: [],
      streamText: "",
      streamUsage: null,
      sending: false,
      waitingReply: false,
      statusText: "",
      selectedFiles: [],
      isNewChatDraft: true,
      activeStreamSessionId: null,
    }),
}));
