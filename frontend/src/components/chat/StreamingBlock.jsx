/**
 * 流式 assistant 消息块。
 */
import { LoadingOutlined, RobotOutlined } from "@ant-design/icons";
import MessageContent from "./MessageContent";

export default function StreamingBlock({ streamText, waitingReply }) {
  const hasText = Boolean(String(streamText || "").trim());

  return (
    <div className="message-row message-assistant streaming-row">
      <div className="message-avatar">
        <RobotOutlined />
      </div>
      <div className="message-body">
        {hasText ? (
          <MessageContent content={streamText} />
        ) : waitingReply ? (
          <div className="loading-dots">
            <LoadingOutlined spin /> 正在思考...
          </div>
        ) : null}
      </div>
    </div>
  );
}
