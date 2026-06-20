import { Link, Navigate, useNavigate } from "react-router-dom";
import { Button, Card, Form, Input, Typography, message } from "antd";
import { LockOutlined, UserOutlined } from "@ant-design/icons";
import { apiFetch } from "../api/client";
import { isAuthenticated, setAuth } from "../api/auth";

const { Text } = Typography;

export default function Login() {
  const navigate = useNavigate();
  const [form] = Form.useForm();

  if (isAuthenticated()) {
    return <Navigate to="/chat" replace />;
  }

  async function onFinish(values) {
    try {
      const data = await apiFetch(
        "/api/auth/login",
        {
          method: "POST",
          body: JSON.stringify({
            username: values.username,
            password: values.password,
          }),
        },
        ""
      );
      setAuth(data.token, data.user);
      message.success("登录成功");
      navigate("/chat");
    } catch (error) {
      message.error(error instanceof Error ? error.message : "登录失败");
    }
  }

  return (
    <div className="page-shell">
      <Card className="hero-card auth-card" bordered={false}>
        <div className="auth-brand">
          <div className="auth-brand-mark">AI</div>
          <div className="auth-brand-title">智能助手</div>
          <div className="auth-brand-sub">AIChat 统一登录</div>
        </div>

        <Form form={form} layout="vertical" onFinish={onFinish} requiredMark={false}>
          <Form.Item
            name="username"
            label="用户名"
            rules={[{ required: true, message: "请输入用户名" }]}
          >
            <Input prefix={<UserOutlined />} placeholder="用户名" autoComplete="username" />
          </Form.Item>

          <Form.Item
            name="password"
            label="密码"
            rules={[{ required: true, message: "请输入密码" }]}
          >
            <Input.Password
              prefix={<LockOutlined />}
              placeholder="密码"
              autoComplete="current-password"
            />
          </Form.Item>

          <Form.Item>
            <Button type="primary" htmlType="submit" block>
              登录
            </Button>
          </Form.Item>
        </Form>

        <Text type="secondary">
          还没有账号？ <Link to="/register">立即注册</Link>
        </Text>
      </Card>
    </div>
  );
}
