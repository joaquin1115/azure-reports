import { useEffect } from "react";
import { Outlet, NavLink, useNavigate } from "react-router-dom";
import { useMsal, useIsAuthenticated } from "@azure/msal-react";
import {
  FileTextOutlined, HistoryOutlined, CalendarOutlined,
  TeamOutlined, BankOutlined, LogoutOutlined,
} from "@ant-design/icons";
import { useUsuarioStore } from "../store/store";

const NAV_ESPECIALISTA = [
  { to: "/generar",   label: "Generar reporte",   icon: <FileTextOutlined /> },
  { to: "/programar", label: "Programar reporte",  icon: <CalendarOutlined /> },
  { to: "/historial", label: "Historial",          icon: <HistoryOutlined /> },
];

const NAV_ADMIN = [
  { to: "/usuarios", label: "Usuarios", icon: <TeamOutlined /> },
  { to: "/clientes", label: "Clientes", icon: <BankOutlined /> },
];

export function AppLayout() {
  const { instance, accounts } = useMsal();
  const isAuthenticated = useIsAuthenticated();
  const navigate = useNavigate();
  const { nombre, rol, setUsuario, clear } = useUsuarioStore();

  useEffect(() => {
    if (!isAuthenticated) {
      navigate("/login");
      return;
    }
    const account = accounts[0];
    if (account) {
      const claims = account.idTokenClaims as Record<string, unknown>;
      const roles = (claims?.roles as string[]) ?? [];
      const r = roles.includes("admin") ? "admin" : "especialista";
      setUsuario(account.name ?? "", account.username, r);
    }
  }, [isAuthenticated]);

  const handleLogout = () => {
    clear();
    instance.logoutPopup();
  };

  const navItems = rol === "admin"
    ? [...NAV_ESPECIALISTA, ...NAV_ADMIN]
    : NAV_ESPECIALISTA;

  return (
    <div className="layout-root">
      <aside className="sidebar">
        <div className="sidebar-logo">
          <div className="logo-text">G<span>&</span>S</div>
          <div className="logo-sub">Azure Report</div>
        </div>
        <nav className="sidebar-nav">
          {navItems.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) => `nav-item${isActive ? " active" : ""}`}
            >
              {item.icon}
              {item.label}
            </NavLink>
          ))}
        </nav>
        <div className="sidebar-user">
          <div className="user-name">{nombre}</div>
          <div className="user-rol">{rol}</div>
          <button className="btn-logout" onClick={handleLogout}>
            <LogoutOutlined /> Cerrar sesión
          </button>
        </div>
      </aside>
      <main className="main-content">
        <Outlet />
      </main>
    </div>
  );
}
