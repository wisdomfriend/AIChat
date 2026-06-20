/**
 * 主区顶栏：侧栏切换 + 模型选择。
 */
import { Button, Select, Tooltip } from "antd";
import { MenuUnfoldOutlined } from "@ant-design/icons";

export default function ChatTopBar({
  sidebarCollapsed,
  onToggleSidebar,
  llmProviders,
  llmProvider,
  onChangeProvider,
}) {
  const providerOptions = llmProviders.map((p) => ({
    value: p.id,
    label: p.display_name || p.name || p.id,
  }));

  const currentLabel =
    providerOptions.find((o) => o.value === llmProvider)?.label || llmProvider || "选择模型";

  return (
    <header className="app-topbar">
      <div className="app-topbar-left">
        {sidebarCollapsed && (
          <Tooltip title="展开侧栏">
            <Button
              type="text"
              className="app-topbar-icon-btn"
              icon={<MenuUnfoldOutlined />}
              onClick={onToggleSidebar}
            />
          </Tooltip>
        )}
        <Select
          className="model-top-select"
          value={llmProvider || undefined}
          options={providerOptions}
          onChange={onChangeProvider}
          placeholder="选择模型"
          variant="borderless"
          popupMatchSelectWidth={200}
          labelRender={() => <span className="model-top-label">{currentLabel}</span>}
        />
      </div>
    </header>
  );
}
