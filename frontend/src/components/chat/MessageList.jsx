/**
 * 消息列表 + 流式输出区。
 */
import { useEffect, useRef } from "react";
import MessageItem from "./MessageItem";
import StreamingBlock from "./StreamingBlock";

export default function MessageList({ messages, streamText, waitingReply, showWelcome }) {
  const bottomRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, streamText, waitingReply]);

  return (
    <div className="chat-messages">
      {showWelcome && messages.length === 0 && !streamText && (
        <div className="welcome-screen">
          <h1>智能政务助手</h1>
          <p>请在下方输入您的问题，系统将为您提供专业、准确的智能问答服务。</p>
        </div>
      )}

      {messages.map((msg) => (
        <MessageItem key={msg.id} message={msg} />
      ))}

      {(waitingReply || streamText) && (
        <StreamingBlock streamText={streamText} waitingReply={waitingReply} />
      )}

      <div ref={bottomRef} />
    </div>
  );
}
