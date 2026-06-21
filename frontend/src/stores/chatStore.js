/**
 * 聊天页 Zustand 状态。
 */
import { create } from "zustand";

export const useChatStore = create((set) => ({
  user: null,
  sessionId: null,
  sessions: [],
  messages: [],
  streamText: "",
  streamUsage: null,
  streamToolCalls: [],
  sending: false,
  waitingReply: false,
  statusText: "",
  llmProviders: [],
  llmProvider: "",
  defaultProvider: "",
  selectedFiles: [],
  knowledgeBases: [],
  selectedKnowledgeBaseIds: [],
  isNewChatDraft: false,
  activeStreamSessionId: null,

  resetStream: () =>
    set({
      streamText: "",
      streamUsage: null,
      streamToolCalls: [],
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
      streamToolCalls: [],
      sending: false,
      waitingReply: false,
      statusText: "",
      selectedFiles: [],
      selectedKnowledgeBaseIds: [],
      isNewChatDraft: true,
      activeStreamSessionId: null,
    }),
}));
