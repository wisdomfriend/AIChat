/**
 * 工具调用步骤展示（流式 / 历史）。
 */
import { toolLabel } from "../../services/chatEvents";

export default function ToolCallList({ tools = [], compact = false }) {
  if (!tools?.length) {
    return null;
  }

  return (
    <div className={`tool-call-list ${compact ? "tool-call-list-compact" : ""}`}>
      {tools.map((tool, index) => (
        <div
          key={`${tool.name}-${index}`}
          className={`tool-call-item tool-call-${tool.status || "done"}`}
        >
          <span className="tool-call-name">{tool.label || toolLabel(tool.name)}</span>
          {tool.status === "running" && <span className="tool-call-spinner" />}
          {tool.result_preview && tool.status === "done" && (
            <span className="tool-call-preview">{tool.result_preview}</span>
          )}
        </div>
      ))}
    </div>
  );
}
