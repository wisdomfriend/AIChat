/**
 * SSE 事件分发 → Zustand store。
 */

function appendAgentBlock(streamText, className, content, prefix = "") {
  const block = `<div class="${className}">${prefix}${content || ""}</div>`;
  return `${streamText || ""}${block}`;
}

function buildAssistantMessage(state, usageOverride) {
  const usage = usageOverride ?? state.streamUsage;
  return {
    id: `assistant-${Date.now()}`,
    role: "assistant",
    content: state.streamText || "",
    created_at: new Date().toISOString(),
    usage: usage || undefined,
  };
}

function usageStatusText(usage) {
  const total = usage?.total_tokens ?? usage?.total;
  return total ? `本次: ${total} tokens` : "完成";
}

/**
 * 将单条 SSE 事件应用到 store。
 *
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

    case "search_start":
      patch.statusText = data.message || "正在搜索...";
      break;
    case "search_complete":
      patch.statusText = data.message || "搜索完成";
      break;
    case "search_error":
      patch.statusText = data.message || "搜索失败";
      break;

    case "agent_think":
      patch.streamText = appendAgentBlock(state.streamText, "agent-think", data.content);
      patch.statusText = "正在思考...";
      break;
    case "agent_action":
      patch.streamText = appendAgentBlock(state.streamText, "agent-action", data.content);
      patch.statusText = "正在执行...";
      break;
    case "agent_observation":
      patch.streamText = appendAgentBlock(state.streamText, "agent-observation", data.content);
      patch.statusText = "观察结果...";
      break;
    case "agent_plan":
      patch.streamText = appendAgentBlock(state.streamText, "agent-plan", data.content, "规划：");
      patch.statusText = "规划完成，正在执行...";
      break;
    case "agent_plan_step":
      patch.streamText = appendAgentBlock(state.streamText, "agent-plan-step", data.content);
      patch.statusText = `规划步骤 ${data.step_num || ""}...`;
      break;
    case "agent_execute_step":
      patch.streamText = appendAgentBlock(state.streamText, "agent-execute-step", data.content);
      patch.statusText = `执行步骤 ${data.step_num || ""}...`;
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
      effects.finalized = true;
      break;
    }

    case "done": {
      const usage = state.streamUsage || data.usage;
      if (String(state.streamText || "").trim() || usage) {
        patch.messages = [...state.messages, buildAssistantMessage(state, usage)];
      }
      patch.streamText = "";
      patch.streamUsage = null;
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

/** 流异常结束或未收到 done 时，将 streamText 落盘为 assistant 消息。 */
export function finalizeStreamIfNeeded(storeApi) {
  const state = storeApi.getState();
  const text = String(state.streamText || "").trim();

  if (!text) {
    storeApi.setState({
      streamText: "",
      streamUsage: null,
    });
    return;
  }

  storeApi.setState({
    messages: [...state.messages, buildAssistantMessage(state)],
    streamText: "",
    streamUsage: null,
    statusText: usageStatusText(state.streamUsage),
  });
}
