/**
 * 聊天输入区：模型选择、Agent 模式、文件上传、发送。
 */
import { useRef } from "react";
import { Button, Select, Upload, message as antMessage } from "antd";
import {
  GlobalOutlined,
  PaperClipOutlined,
  SendOutlined,
  StopOutlined,
} from "@ant-design/icons";
import { formatBytes, getTextSizeInBytes, isImageFile, MAX_MESSAGE_BYTES } from "../../services/chatApi";

const AGENT_OPTIONS = [
  { value: "normal", label: "普通聊天" },
  { value: "web_search", label: "联网搜索" },
  { value: "react", label: "推理与行动" },
  { value: "plan_execute", label: "规划与执行" },
];

export default function ChatComposer({
  disabled,
  sending,
  waitingReply,
  llmProviders,
  llmProvider,
  agentMode,
  selectedFiles,
  statusText,
  onChangeProvider,
  onChangeAgentMode,
  onChangeFiles,
  onSend,
  onStop,
}) {
  const textareaRef = useRef(null);
  const fileInputRef = useRef(null);

  function handleKeyDown(e) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      if (!disabled && !sending && !waitingReply) {
        submit();
      }
    }
  }

  function submit() {
    const text = textareaRef.current?.value?.trim() || "";
    if (!text) {
      return;
    }
    const size = getTextSizeInBytes(text);
    if (size > MAX_MESSAGE_BYTES) {
      antMessage.error(`消息过长！当前 ${formatBytes(size)}，最大 ${formatBytes(MAX_MESSAGE_BYTES)}`);
      return;
    }
    onSend(text);
    if (textareaRef.current) {
      textareaRef.current.value = "";
      textareaRef.current.style.height = "auto";
    }
  }

  async function handleFileChange(e) {
    const files = Array.from(e.target.files || []);
    e.target.value = "";
    if (!files.length) {
      return;
    }
    const next = [...selectedFiles];
    for (const file of files) {
      next.push({
        id: `local-${Date.now()}-${Math.random().toString(16).slice(2)}`,
        file,
        original_filename: file.name,
        file_size: file.size,
        is_image: isImageFile(file.name),
        uploaded: false,
        uploading: false,
      });
    }
    onChangeFiles(next);
  }

  function removeFile(id) {
    onChangeFiles(selectedFiles.filter((f) => f.id !== id));
  }

  const providerOptions = llmProviders.map((p) => ({
    value: p.id,
    label: p.display_name || p.name || p.id,
  }));

  return (
    <div className="chat-input-area">
      <div className="input-container">
        <div className="model-selector-container">
          <label htmlFor="llmProviderSelect">模型:</label>
          <Select
            id="llmProviderSelect"
            value={llmProvider || undefined}
            style={{ minWidth: 180 }}
            options={providerOptions}
            onChange={onChangeProvider}
            placeholder="选择模型"
          />
          <Select
            value={agentMode}
            style={{ minWidth: 140 }}
            options={AGENT_OPTIONS}
            onChange={onChangeAgentMode}
          />
          <Button
            type={agentMode === "web_search" ? "primary" : "default"}
            icon={<GlobalOutlined />}
            onClick={() => onChangeAgentMode("web_search")}
          >
            联网
          </Button>
        </div>

        {selectedFiles.length > 0 && (
          <div className="selected-files">
            {selectedFiles.map((f) => (
              <div key={f.id} className="selected-file-chip">
                <span>{f.original_filename}</span>
                <button type="button" onClick={() => removeFile(f.id)}>
                  ×
                </button>
              </div>
            ))}
          </div>
        )}

        <div className="input-wrapper">
          <textarea
            ref={textareaRef}
            className="message-input"
            placeholder="输入消息..."
            rows={1}
            disabled={disabled || sending}
            onKeyDown={handleKeyDown}
            onInput={(e) => {
              e.target.style.height = "auto";
              e.target.style.height = `${e.target.scrollHeight}px`;
            }}
          />
          <input
            ref={fileInputRef}
            type="file"
            multiple
            hidden
            onChange={handleFileChange}
            accept=".txt,.md,.py,.json,.js,.ts,.html,.css,.xml,.yaml,.yml,.pdf,.docx,.xlsx,.jpg,.jpeg,.png,.gif,.webp,.bmp,.svg"
          />
          <Button
            className="upload-button"
            icon={<PaperClipOutlined />}
            onClick={() => fileInputRef.current?.click()}
            disabled={disabled || sending}
          />
          {waitingReply || sending ? (
            <Button danger icon={<StopOutlined />} onClick={onStop} />
          ) : (
            <Button
              type="primary"
              className="send-button"
              icon={<SendOutlined />}
              onClick={submit}
              disabled={disabled}
            />
          )}
        </div>

        <div className="input-footer">
          <span className="token-info">{statusText || "就绪"}</span>
          <span className="input-hint">Enter 发送，Shift+Enter 换行</span>
        </div>
      </div>
    </div>
  );
}
