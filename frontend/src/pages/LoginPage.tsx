import { useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { useMsal, useIsAuthenticated } from "@azure/msal-react";
import { loginRequest } from "../services/authConfig";
import { Button, Spin } from "antd";
import { WindowsOutlined } from "@ant-design/icons";

export function LoginPage() {
  const { instance, inProgress } = useMsal();
  const isAuthenticated = useIsAuthenticated();
  const navigate = useNavigate();

  useEffect(() => {
    if (isAuthenticated) navigate("/");
  }, [isAuthenticated]);

  const handleLogin = async () => {
    try {
      console.log(import.meta.env.VITE_AZURE_TENANT_ID);
      await instance.loginPopup(loginRequest);
      navigate("/");
    } catch (e) {
      console.error("Login error:", e);
    }
  };

  return (
    <div className="login-page">
      <div className="login-card">
        <div className="login-logo">G<span>&</span>S</div>
        <div className="login-subtitle">
          Sistema de reportes de consumo de Azure
        </div>
        {inProgress !== "none" ? (
          <Spin size="large" />
        ) : (
          <Button
            type="primary"
            size="large"
            icon={<WindowsOutlined />}
            onClick={handleLogin}
            style={{ width: "100%", height: 44, fontWeight: 600 }}
          >
            Iniciar sesión con Microsoft
          </Button>
        )}
        <p style={{ marginTop: 24, fontSize: 12, color: "#94a3b8" }}>
          Usa tu cuenta corporativa de G&S
        </p>
      </div>
    </div>
  );
}
