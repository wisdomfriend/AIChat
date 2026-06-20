/**
 * 流式 assistant 消息块。
 */
import MessageContent from "./MessageContent";
import MessageActions from "./MessageActions";
import ToolCallList from "./ToolCallList";

export default function StreamingBlock({ streamText, streamToolCalls, waitingReply }) {
  const hasText = Boolean(String(streamText || "").trim());
  const hasTools = Boolean(streamToolCalls?.length);

  return (
    <div className="message-row message-assistant streaming-row">
      <div className="message-body message-body-full">
        {hasTools && <ToolCallList tools={streamToolCalls} />}
        {hasText ? (
          <div className="streaming-content">
            <MessageContent content={streamText} />
            {waitingReply && <span className="streaming-cursor" />}
          </div>
        ) : waitingReply ? (
          <div className="streaming-thinking">
            <span className="thinking-dot" />
            <span className="thinking-dot" />
            <span className="thinking-dot" />
          </div>
        ) : null}
        {hasText && !waitingReply && <MessageActions content={streamText} />}
      </div>
    </div>
  );
}
