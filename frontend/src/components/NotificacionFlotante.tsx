import { useEffect } from "react";
import { CheckCircleOutlined, CloseCircleOutlined, InfoCircleOutlined, CloseOutlined } from "@ant-design/icons";
import { useNotifStore } from "../store/store";

export function NotificacionFlotante() {
  const { mensaje, tipo, limpiar } = useNotifStore();

  useEffect(() => {
    if (!mensaje) return;
    const t = setTimeout(limpiar, 5000);
    return () => clearTimeout(t);
  }, [mensaje]);

  if (!mensaje) return null;

  const iconMap = {
    success: <CheckCircleOutlined style={{ color: "#10b981", fontSize: 20 }} />,
    error:   <CloseCircleOutlined style={{ color: "#ef4444", fontSize: 20 }} />,
    info:    <InfoCircleOutlined  style={{ color: "#1987af", fontSize: 20 }} />,
  };

  return (
    <div className={`notif-float ${tipo}`}>
      {iconMap[tipo]}
      <span style={{ flex: 1, fontSize: 13.5, fontWeight: 500 }}>{mensaje}</span>
      <button
        onClick={limpiar}
        style={{ background: "none", border: "none", cursor: "pointer", color: "#94a3b8" }}
      >
        <CloseOutlined />
      </button>
    </div>
  );
}
