/**
 * 单条聊天消息（ChatGPT 式对齐）。
 */
import MessageContent from "./MessageContent";
import AuthenticatedImage from "./AuthenticatedImage";

export default function MessageItem({ message }) {
  const isUser = message.role === "user";

  if (isUser) {
    return (
      <div className="message-row message-user">
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
          <MessageContent content={message.content} isUser />
        </div>
      </div>
    );
  }

  return (
    <div className="message-row message-assistant">
      <div className="message-body message-body-full">
        {message.files?.length > 0 && (
          <div className="message-files">
            {message.files.map((file) => (
              <div key={file.id} className="file-chip">
                {file.filename}
              </div>
            ))}
          </div>
        )}
        <MessageContent content={message.content} />
        {message.usage && (
          <div className="message-usage">
            tokens: {message.usage.total_tokens ?? message.usage.total ?? "-"}
          </div>
        )}
      </div>
    </div>
  );
}
