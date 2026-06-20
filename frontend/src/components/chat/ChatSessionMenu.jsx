/**
 * 会话顶部三点菜单：固定 / 解除固定 / 删除。
 */
import { Button, Dropdown, Modal } from "antd";
import { DeleteOutlined, EllipsisOutlined, PushpinOutlined } from "@ant-design/icons";

export default function ChatSessionMenu({ session, onPin, onUnpin, onDelete }) {
  if (!session) {
    return null;
  }

  const menuItems = session.is_pinned
    ? [
        {
          key: "unpin",
          icon: <PushpinOutlined />,
          label: "解除固定",
          onClick: onUnpin,
        },
      ]
    : [
        {
          key: "pin",
          icon: <PushpinOutlined />,
          label: "固定",
          onClick: onPin,
        },
      ];

  menuItems.push(
    { type: "divider" },
    {
      key: "delete",
      icon: <DeleteOutlined />,
      label: "删除",
      danger: true,
      onClick: () => {
        Modal.confirm({
          title: "删除对话",
          content: "确定删除此对话？此操作不可恢复。",
          okText: "删除",
          okType: "danger",
          cancelText: "取消",
          onOk: onDelete,
        });
      },
    }
  );

  return (
    <header className="chat-session-header">
      <h2 className="chat-session-title">{session.title || `会话 ${session.id}`}</h2>
      <Dropdown menu={{ items: menuItems }} trigger={["click"]} placement="bottomRight">
        <Button type="text" className="chat-session-menu-btn" icon={<EllipsisOutlined />} />
      </Dropdown>
    </header>
  );
}
