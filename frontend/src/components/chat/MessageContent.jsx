/**
 * 消息内容渲染（Markdown / Agent HTML / 用户纯文本）。
 */
import { useMemo } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import rehypeKatex from "rehype-katex";
import rehypeSanitize from "rehype-sanitize";
import DOMPurify from "dompurify";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { oneDark } from "react-syntax-highlighter/dist/esm/styles/prism";
import "katex/dist/katex.min.css";

const AGENT_MARKERS = ["agent-think", "agent-action", "agent-observation", "agent-plan"];

function hasAgentHtml(content) {
  return AGENT_MARKERS.some((m) => String(content).includes(m));
}

export default function MessageContent({ content, isUser = false }) {
  const safeHtml = useMemo(() => {
    if (isUser || !hasAgentHtml(content)) {
      return "";
    }
    return DOMPurify.sanitize(String(content || ""), {
      ADD_TAGS: ["div", "span", "pre", "code"],
      ADD_ATTR: ["class"],
    });
  }, [content, isUser]);

  if (isUser) {
    return <div className="message-text user-text">{content}</div>;
  }

  if (hasAgentHtml(content)) {
    return <div className="message-html" dangerouslySetInnerHTML={{ __html: safeHtml }} />;
  }

  return (
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
  );
}
