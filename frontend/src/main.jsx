import React from "react";
import ReactDOM from "react-dom/client";
import { ConfigProvider } from "antd";
import zhCN from "antd/locale/zh_CN";
import App from "./App";
import { govEnterpriseTheme } from "./theme/govEnterprise";
import "./styles.css";

ReactDOM.createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <ConfigProvider locale={zhCN} theme={govEnterpriseTheme}>
      <App />
    </ConfigProvider>
  </React.StrictMode>
);
