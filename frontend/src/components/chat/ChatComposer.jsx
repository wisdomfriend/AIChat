/**
 * ChatGPT 式圆角输入框 + 快捷 chips。
 */
import { useRef, useState } from "react";
import { Button, Dropdown, Select, message as antMessage } from "antd";
import {
  EditOutlined,
  FileSearchOutlined,
  GlobalOutlined,
  PaperClipOutlined,
  PlusOutlined,
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

const QUICK_PROMPTS = [
  {
    key: "doc",
    label: "写一份通知",
    icon: <EditOutlined />,
    text: "请帮我写一份正式的通知公文，主题是：",
  },
  {
    key: "summary",
    label: "总结要点",
    icon: <FileSearchOutlined />,
    text: "请用条目形式总结以下内容的核心要点：",
  },
  {
    key: "search",
    label: "联网查询",
    icon: <GlobalOutlined />,
    text: "请搜索并整理以下问题的最新信息：",
    agentMode: "web_search",
  },
];

export default function ChatComposer({
  disabled,
  sending,
  waitingReply,
  agentMode,
  selectedFiles,
  statusText,
  onChangeAgentMode,
  onChangeFiles,
  onSend,
  onStop,
  centered = false,
}) {
  const textareaRef = useRef(null);
  const fileInputRef = useRef(null);
  const [toolsOpen, setToolsOpen] = useState(false);

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

  function applyQuickPrompt(item) {
    if (item.agentMode) {
      onChangeAgentMode(item.agentMode);
    }
    if (textareaRef.current) {
      textareaRef.current.value = item.text;
      textareaRef.current.focus();
      textareaRef.current.style.height = "auto";
      textareaRef.current.style.height = `${textareaRef.current.scrollHeight}px`;
    }
  }

  function handleFileChange(e) {
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
    setToolsOpen(false);
  }

  function removeFile(id) {
    onChangeFiles(selectedFiles.filter((f) => f.id !== id));
  }

  const toolMenuItems = [
    {
      key: "file",
      icon: <PaperClipOutlined />,
      label: "上传文件",
      onClick: () => fileInputRef.current?.click(),
    },
    {
      key: "web",
      icon: <GlobalOutlined />,
      label: "联网搜索",
      onClick: () => onChangeAgentMode("web_search"),
    },
  ];

  return (
    <div className={`chat-input-area ${centered ? "chat-input-centered" : ""}`}>
      <div className="composer-shell">
        {centered && (
          <div className="composer-quick-chips">
            {QUICK_PROMPTS.map((item) => (
              <button
                key={item.key}
                type="button"
                className="composer-chip"
                onClick={() => applyQuickPrompt(item)}
                disabled={disabled || sending}
              >
                {item.icon}
                <span>{item.label}</span>
              </button>
            ))}
          </div>
        )}

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

        <div className="composer-pill">
          <Dropdown
            menu={{ items: toolMenuItems }}
            trigger={["click"]}
            open={toolsOpen}
            onOpenChange={setToolsOpen}
          >
            <Button type="text" className="composer-plus-btn" icon={<PlusOutlined />} disabled={disabled || sending} />
          </Dropdown>

          <textarea
            ref={textareaRef}
            className="composer-input"
            placeholder="输入您的问题..."
            rows={1}
            disabled={disabled || sending}
            onKeyDown={handleKeyDown}
            onInput={(e) => {
              e.target.style.height = "auto";
              e.target.style.height = `${Math.min(e.target.scrollHeight, 200)}px`;
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

          {waitingReply || sending ? (
            <Button type="text" danger className="composer-send-btn" icon={<StopOutlined />} onClick={onStop} />
          ) : (
            <Button
              type="primary"
              shape="circle"
              className="composer-send-btn"
              icon={<SendOutlined />}
              onClick={submit}
              disabled={disabled}
            />
          )}
        </div>

        <div className="composer-toolbar">
          <Select
            size="small"
            value={agentMode}
            variant="borderless"
            className="composer-mode-select"
            options={AGENT_OPTIONS}
            onChange={onChangeAgentMode}
            popupMatchSelectWidth={140}
          />
          <span className="composer-status">{statusText || "Enter 发送 · Shift+Enter 换行"}</span>
        </div>
      </div>
    </div>
  );
}
