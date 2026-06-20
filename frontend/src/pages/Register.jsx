import AppLogo from "../components/AppLogo";
import { Link, Navigate, useNavigate } from "react-router-dom";
import { Button, Card, Form, Input, Typography, message } from "antd";
import { LockOutlined, UserOutlined } from "@ant-design/icons";
import { apiFetch } from "../api/client";
import { isAuthenticated } from "../api/auth";

const { Text } = Typography;

export default function Register() {
  const navigate = useNavigate();
  const [form] = Form.useForm();

  if (isAuthenticated()) {
    return <Navigate to="/chat" replace />;
  }

  async function onFinish(values) {
    try {
      await apiFetch(
        "/api/auth/register",
        {
          method: "POST",
          body: JSON.stringify({
            username: values.username,
            password: values.password,
            password_confirm: values.password_confirm,
          }),
        },
        ""
      );
      message.success("注册成功，请登录");
      navigate("/login");
    } catch (error) {
      message.error(error instanceof Error ? error.message : "注册失败");
    }
  }

  return (
    <div className="page-shell">
      <Card className="hero-card auth-card" bordered={false}>
        <div className="auth-brand">
          <AppLogo size={52} className="auth-brand-logo" />
          <div className="auth-brand-title">账号注册</div>
          <div className="auth-brand-sub">创建账号后即可使用智能对话服务</div>
        </div>

        <Form form={form} layout="vertical" onFinish={onFinish} requiredMark={false}>
          <Form.Item
            name="username"
            label="用户名"
            rules={[
              { required: true, message: "请输入用户名" },
              { min: 3, message: "至少 3 个字符" },
              { max: 20, message: "最多 20 个字符" },
            ]}
          >
            <Input prefix={<UserOutlined />} placeholder="3-20 位字母数字下划线" />
          </Form.Item>

          <Form.Item
            name="password"
            label="密码"
            rules={[
              { required: true, message: "请输入密码" },
              { min: 6, message: "至少 6 个字符" },
            ]}
          >
            <Input.Password prefix={<LockOutlined />} placeholder="至少 6 位" />
          </Form.Item>

          <Form.Item
            name="password_confirm"
            label="确认密码"
            dependencies={["password"]}
            rules={[
              { required: true, message: "请再次输入密码" },
              ({ getFieldValue }) => ({
                validator(_, value) {
                  if (!value || getFieldValue("password") === value) {
                    return Promise.resolve();
                  }
                  return Promise.reject(new Error("两次输入的密码不一致"));
                },
              }),
            ]}
          >
            <Input.Password prefix={<LockOutlined />} placeholder="再次输入密码" />
          </Form.Item>

          <Form.Item>
            <Button type="primary" htmlType="submit" block>
              注册
            </Button>
          </Form.Item>
        </Form>

        <Text type="secondary">
          已有账号？ <Link to="/login">返回登录</Link>
        </Text>
      </Card>
    </div>
  );
}
