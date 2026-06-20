/**
 * POST SSE 聊天流（@microsoft/fetch-event-source）。
 */
import { fetchEventSource } from "@microsoft/fetch-event-source";
import { getToken } from "../api/auth";
import { buildUrl } from "../api/client";
import { applyChatEvent, finalizeStreamIfNeeded } from "../services/chatEvents";

export function createChatStreamController() {
  return new AbortController();
}

/**
 * 发送聊天消息并消费 SSE 流。
 *
 * @param {object} params
 * @param {string} params.message
 * @param {number|null} params.sessionId
 * @param {number[]} params.fileIds
 * @param {string} params.llmProvider
 * @param {string} params.agentMode
 * @param {object} params.storeApi - useChatStore 实例（含 getState/setState）
 * @param {AbortSignal} params.signal
 * @param {() => void} [params.onReloadSessions]
 */
export async function streamChatMessage({
  message,
  sessionId,
  fileIds,
  llmProvider,
  agentMode,
  storeApi,
  signal,
  onReloadSessions,
}) {
  const token = getToken();
  let gotDone = false;
  let streamError = null;

  const body = {
    message,
    session_id: sessionId || undefined,
    file_ids: fileIds || [],
    llm_provider: llmProvider || undefined,
    agent_mode: agentMode || "normal",
  };

  try {
    await fetchEventSource(buildUrl("/api/chat"), {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: JSON.stringify(body),
      signal,
      openWhenHidden: true,
      async onopen(response) {
        if (response.ok) {
          return;
        }
        const text = await response.text().catch(() => "");
        let messageText = `请求失败: ${response.status}`;
        try {
          const line = text.split("\n").find((l) => l.startsWith("data: "));
          if (line) {
            const parsed = JSON.parse(line.slice(6));
            messageText = parsed.message || messageText;
          }
        } catch {
          // ignore parse error
        }
        throw new Error(messageText);
      },
      onmessage(ev) {
        if (!ev.data?.trim()) {
          return;
        }
        let data;
        try {
          data = JSON.parse(ev.data);
        } catch {
          return;
        }

        const expectedSession = storeApi.getState().activeStreamSessionId ?? sessionId;
        if (
          data.type !== "session_id" &&
          expectedSession != null &&
          storeApi.getState().sessionId != null &&
          storeApi.getState().sessionId !== expectedSession &&
          storeApi.getState().activeStreamSessionId !== storeApi.getState().sessionId
        ) {
          return;
        }

        const effects = applyChatEvent(data, storeApi);
        if (effects.error) {
          streamError = new Error(effects.error);
        }
        if (effects.reloadSessions && onReloadSessions) {
          onReloadSessions();
        }
        if (effects.finalized) {
          gotDone = true;
        }
      },
      onerror(err) {
        throw err;
      },
    });
  } catch (err) {
    if (err?.name === "AbortError") {
      finalizeStreamIfNeeded(storeApi);
      return;
    }
    throw streamError || err;
  }

  if (streamError) {
    throw streamError;
  }

  if (!gotDone) {
    finalizeStreamIfNeeded(storeApi);
  }
}
