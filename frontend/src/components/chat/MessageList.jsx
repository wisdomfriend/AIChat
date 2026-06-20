/**
 * 消息列表 + 流式输出区。
 */
import { useEffect, useRef } from "react";
import MessageItem from "./MessageItem";
import StreamingBlock from "./StreamingBlock";

export default function MessageList({ messages, streamText, streamToolCalls, waitingReply, showWelcome }) {
  const bottomRef = useRef(null);
  const hasStreamingTools = (streamToolCalls?.length ?? 0) > 0;
  const showStreaming = waitingReply || Boolean(String(streamText || "").trim()) || hasStreamingTools;
  const isEmpty = messages.length === 0 && !streamText && !hasStreamingTools;

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, streamText, streamToolCalls, waitingReply]);

  return (
    <div className={`chat-messages ${isEmpty && showWelcome ? "chat-messages-empty" : ""}`}>
      {showWelcome && isEmpty && (
        <div className="welcome-center">
          <h1 className="welcome-heading">从哪里开始？</h1>
        </div>
      )}

      {!isEmpty && (
        <div className="message-stream">
          {messages.map((msg) => (
            <MessageItem key={msg.id} message={msg} />
          ))}

          {showStreaming && (
            <StreamingBlock
              streamText={streamText}
              streamToolCalls={streamToolCalls}
              waitingReply={waitingReply}
            />
          )}
        </div>
      )}

      <div ref={bottomRef} />
    </div>
  );
}
