/**
 * 政企风格后台布局（Dashboard / Admin）。
 */
import { useMemo } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { Layout, Menu, Typography, Dropdown, Space, Button } from "antd";
import {
  BarChartOutlined,
  CommentOutlined,
  LogoutOutlined,
  SettingOutlined,
  UserOutlined,
} from "@ant-design/icons";
import { clearAuth, getStoredUser } from "../../api/auth";
import "./AppLayout.css";

const { Header, Sider, Content } = Layout;
const { Text } = Typography;

export default function AppLayout({ title, children }) {
  const navigate = useNavigate();
  const location = useLocation();
  const user = getStoredUser();

  const selectedKey = useMemo(() => {
    if (location.pathname.startsWith("/admin")) {
      return "admin";
    }
    if (location.pathname.startsWith("/dashboard")) {
      return "dashboard";
    }
    return "chat";
  }, [location.pathname]);

  const menuItems = useMemo(() => {
    const items = [
      { key: "chat", icon: <CommentOutlined />, label: "智能对话" },
    ];
    if (user?.is_admin) {
      items.push(
        { key: "dashboard", icon: <BarChartOutlined />, label: "数据统计" },
        { key: "admin", icon: <SettingOutlined />, label: "系统管理" }
      );
    }
    return items;
  }, [user?.is_admin]);

  function handleMenuClick({ key }) {
    if (key === "chat") {
      navigate("/chat");
    } else if (key === "dashboard") {
      navigate("/dashboard");
    } else if (key === "admin") {
      navigate("/admin");
    }
  }

  function handleLogout() {
    clearAuth();
    navigate("/login", { replace: true });
  }

  const userMenu = {
    items: [
      {
        key: "logout",
        icon: <LogoutOutlined />,
        label: "退出登录",
        onClick: handleLogout,
      },
    ],
  };

  return (
    <Layout className="gov-app-layout">
      <Sider width={220} theme="dark" className="gov-sider">
        <div className="gov-brand">
          <div className="gov-brand-mark">AI</div>
          <div>
            <div className="gov-brand-title">智能政务助手</div>
            <div className="gov-brand-sub">AIChat 平台</div>
          </div>
        </div>
        <Menu
          theme="dark"
          mode="inline"
          selectedKeys={[selectedKey]}
          items={menuItems}
          onClick={handleMenuClick}
        />
      </Sider>

      <Layout>
        <Header className="gov-header">
          <Text className="gov-header-title">{title}</Text>
          <Space>
            <Dropdown menu={userMenu} placement="bottomRight">
              <Button type="text" className="gov-user-btn">
                <UserOutlined />
                <span>{user?.username || "用户"}</span>
              </Button>
            </Dropdown>
          </Space>
        </Header>

        <Content className="gov-content">{children}</Content>
      </Layout>
    </Layout>
  );
}
