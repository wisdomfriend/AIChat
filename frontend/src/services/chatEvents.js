/**
 * SSE 事件分发 → Zustand store。
 */

const TOOL_LABELS = {
  web_search: "联网搜索",
  get_time_info: "查询时间",
};

function toolLabel(name) {
  return TOOL_LABELS[name] || name || "工具";
}

function buildAssistantMessage(state, usageOverride) {
  const usage = usageOverride ?? state.streamUsage;
  const toolCalls = state.streamToolCalls?.length ? state.streamToolCalls : undefined;
  return {
    id: `assistant-${Date.now()}`,
    role: "assistant",
    content: state.streamText || "",
    created_at: new Date().toISOString(),
    usage: usage || undefined,
    metadata: toolCalls ? { tool_calls: toolCalls } : undefined,
  };
}

function usageStatusText(usage) {
  const total = usage?.total_tokens ?? usage?.total;
  return total ? `本次: ${total} tokens` : "完成";
}

/**
 * @returns {{ error: string|null, reloadSessions: boolean, finalized: boolean }}
 */
export function applyChatEvent(data, storeApi) {
  const effects = {
    error: null,
    reloadSessions: false,
    finalized: false,
  };

  const state = storeApi.getState();
  const patch = {};

  switch (data.type) {
    case "content":
      patch.streamText = `${state.streamText || ""}${data.content || ""}`;
      break;

    case "session_id":
      patch.sessionId = data.session_id;
      patch.isNewChatDraft = false;
      patch.activeStreamSessionId = data.session_id;
      effects.reloadSessions = true;
      break;

    case "session_title":
      effects.reloadSessions = true;
      break;

    case "usage":
      patch.streamUsage = data.usage;
      break;

    case "tool_start": {
      const next = [...(state.streamToolCalls || [])];
      next.push({
        name: data.tool,
        label: toolLabel(data.tool),
        status: "running",
        args: data.args || {},
      });
      patch.streamToolCalls = next;
      patch.statusText = `${toolLabel(data.tool)}…`;
      break;
    }

    case "tool_end": {
      const next = [...(state.streamToolCalls || [])];
      for (let i = next.length - 1; i >= 0; i -= 1) {
        if (next[i].name === data.tool && next[i].status === "running") {
          next[i] = {
            ...next[i],
            status: "done",
            result_preview: data.result_preview || "",
          };
          break;
        }
      }
      patch.streamToolCalls = next;
      patch.statusText = `${toolLabel(data.tool)} 完成`;
      break;
    }

    case "tool_status":
      patch.statusText = data.message || patch.statusText || "正在执行…";
      break;

    case "error": {
      const message = data.message || "未知错误";
      effects.error = message;
      patch.statusText = "请求失败";
      patch.messages = [
        ...state.messages,
        {
          id: `error-${Date.now()}`,
          role: "assistant",
          content: `错误: ${message}`,
          created_at: new Date().toISOString(),
        },
      ];
      patch.streamText = "";
      patch.streamUsage = null;
      patch.streamToolCalls = [];
      effects.finalized = true;
      break;
    }

    case "done": {
      const usage = state.streamUsage || data.usage;
      const toolCalls = data.tool_calls?.length ? data.tool_calls : state.streamToolCalls;
      if (toolCalls?.length) {
        patch.streamToolCalls = toolCalls.map((t) => ({
          ...t,
          label: toolLabel(t.name),
          status: "done",
        }));
      }
      if (String(state.streamText || "").trim() || usage || toolCalls?.length) {
        const merged = { ...state, ...patch, streamUsage: usage, streamToolCalls: patch.streamToolCalls ?? state.streamToolCalls };
        patch.messages = [...state.messages, buildAssistantMessage(merged, usage)];
      }
      patch.streamText = "";
      patch.streamUsage = null;
      patch.streamToolCalls = [];
      patch.statusText = usageStatusText(usage);
      effects.finalized = true;
      break;
    }

    default:
      break;
  }

  if (Object.keys(patch).length > 0) {
    storeApi.setState(patch);
  }

  return effects;
}

export function finalizeStreamIfNeeded(storeApi) {
  const state = storeApi.getState();
  const text = String(state.streamText || "").trim();
  const tools = state.streamToolCalls || [];

  if (!text && !tools.length) {
    storeApi.setState({
      streamText: "",
      streamUsage: null,
      streamToolCalls: [],
    });
    return;
  }

  storeApi.setState({
    messages: [...state.messages, buildAssistantMessage(state)],
    streamText: "",
    streamUsage: null,
    streamToolCalls: [],
    statusText: usageStatusText(state.streamUsage),
  });
}

export { toolLabel };
