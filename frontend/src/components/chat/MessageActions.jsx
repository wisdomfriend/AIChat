/**
 * 消息下方操作栏（复制）。
 */
import { message } from "antd";
import { CheckOutlined, CopyOutlined } from "@ant-design/icons";
import { useState } from "react";

function toPlainText(content) {
  const raw = String(content || "");
  if (!raw.includes("<")) {
    return raw;
  }
  const div = document.createElement("div");
  div.innerHTML = raw;
  return div.textContent || div.innerText || raw;
}

export default function MessageActions({ content }) {
  const [copied, setCopied] = useState(false);
  const text = toPlainText(content);

  async function handleCopy() {
    if (!text.trim()) {
      return;
    }
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      message.success("已复制");
      setTimeout(() => setCopied(false), 2000);
    } catch {
      message.error("复制失败");
    }
  }

  if (!text.trim()) {
    return null;
  }

  return (
    <div className="message-actions">
      <button type="button" className="message-action-btn" onClick={handleCopy}>
        {copied ? <CheckOutlined /> : <CopyOutlined />}
        <span>{copied ? "已复制" : "复制"}</span>
      </button>
    </div>
  );
}
