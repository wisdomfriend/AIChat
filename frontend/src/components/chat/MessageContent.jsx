/**
 * 消息内容渲染（Markdown / 工具摘要 / 用户纯文本）。
 */
import { useMemo } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import rehypeKatex from "rehype-katex";
import rehypeSanitize from "rehype-sanitize";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { oneDark } from "react-syntax-highlighter/dist/esm/styles/prism";
import ToolCallList from "./ToolCallList";
import "katex/dist/katex.min.css";

export default function MessageContent({ content, isUser = false, metadata = null }) {
  const toolCalls = useMemo(() => metadata?.tool_calls || [], [metadata]);

  if (isUser) {
    return <div className="message-text user-text">{content}</div>;
  }

  return (
    <div className="message-assistant-wrap">
      {toolCalls.length > 0 && <ToolCallList tools={toolCalls} compact />}
      <div className="message-markdown">
        <ReactMarkdown
          remarkPlugins={[remarkGfm]}
          rehypePlugins={[rehypeKatex, rehypeSanitize]}
          components={{
            code({ inline, className, children, ...props }) {
              const match = /language-(\w+)/.exec(className || "");
              if (!inline && match) {
                return (
                  <SyntaxHighlighter style={oneDark} language={match[1]} PreTag="div" {...props}>
                    {String(children).replace(/\n$/, "")}
                  </SyntaxHighlighter>
                );
              }
              return (
                <code className={className} {...props}>
                  {children}
                </code>
              );
            },
          }}
        >
          {String(content || "")}
        </ReactMarkdown>
      </div>
    </div>
  );
}
