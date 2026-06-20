/**
 * 流式 assistant 消息块。
 */
import MessageContent from "./MessageContent";

export default function StreamingBlock({ streamText, waitingReply }) {
  const hasText = Boolean(String(streamText || "").trim());

  return (
    <div className="message-row message-assistant streaming-row">
      <div className="message-body message-body-full">
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
      </div>
    </div>
  );
}
