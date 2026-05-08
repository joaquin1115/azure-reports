import React from "react";
import ReactDOM from "react-dom/client";
import { PublicClientApplication } from "@azure/msal-browser";
import { MsalProvider } from "@azure/msal-react";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { ConfigProvider } from "antd";
import esES from "antd/locale/es_ES";

import { msalConfig } from "./services/authConfig";
import { AppLayout } from "./components/AppLayout";
import { LoginPage } from "./pages/LoginPage";
import { GenerarReportePage } from "./pages/GenerarReportePage";
import { HistorialPage } from "./pages/HistorialPage";
import { ProgramarReportePage } from "./pages/ProgramarReportePage";
import { UsuariosPage } from "./pages/UsuariosPage";
import { ClientesPage } from "./pages/ClientesPage";
import { NotificacionFlotante } from "./components/NotificacionFlotante";
import "./styles/global.css";

export const msalInstance = new PublicClientApplication(msalConfig);

const antdTheme = {
  token: {
    colorPrimary: "#1987af",
    colorWarning: "#ffbe1e",
    borderRadius: 8,
    fontFamily: "'Plus Jakarta Sans', sans-serif",
  },
};

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <MsalProvider instance={msalInstance}>
      <ConfigProvider locale={esES} theme={antdTheme}>
        <BrowserRouter>
          <NotificacionFlotante />
          <Routes>
            <Route path="/login" element={<LoginPage />} />
            <Route path="/" element={<AppLayout />}>
              <Route index element={<Navigate to="/generar" replace />} />
              <Route path="generar" element={<GenerarReportePage />} />
              <Route path="historial" element={<HistorialPage />} />
              <Route path="programar" element={<ProgramarReportePage />} />
              <Route path="usuarios" element={<UsuariosPage />} />
              <Route path="clientes" element={<ClientesPage />} />
            </Route>
          </Routes>
        </BrowserRouter>
      </ConfigProvider>
    </MsalProvider>
  </React.StrictMode>
);
