/**
 * 单条聊天消息行。
 */
import { UserOutlined, RobotOutlined } from "@ant-design/icons";
import MessageContent from "./MessageContent";
import AuthenticatedImage from "./AuthenticatedImage";

export default function MessageItem({ message }) {
  const isUser = message.role === "user";

  return (
    <div className={`message-row ${isUser ? "message-user" : "message-assistant"}`}>
      <div className="message-avatar">{isUser ? <UserOutlined /> : <RobotOutlined />}</div>
      <div className="message-body">
        {message.files?.length > 0 && (
          <div className="message-files">
            {message.files.map((file) =>
              file.is_image || /\.(png|jpe?g|gif|webp|bmp|svg)$/i.test(file.filename || "") ? (
                <AuthenticatedImage key={file.id} fileId={file.id} alt={file.filename} />
              ) : (
                <div key={file.id} className="file-chip">
                  {file.filename}
                </div>
              )
            )}
          </div>
        )}
        <MessageContent content={message.content} isUser={isUser} />
        {message.usage && (
          <div className="message-usage">
            tokens: {message.usage.total_tokens ?? message.usage.total ?? "-"}
          </div>
        )}
      </div>
    </div>
  );
}
