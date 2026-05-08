import { useState, useEffect } from "react";
import { Table, Select, Button, Tag, Empty } from "antd";
import { DownloadOutlined, ReloadOutlined } from "@ant-design/icons";
import type { ColumnsType } from "antd/es/table";
import api from "../services/apiClient";
import { useNotifStore } from "../store/store";
import dayjs from "dayjs";

type Reporte = {
  id: string;
  cliente: { id: string; nombre: string };
  periodo_mes: number;
  periodo_anio: number;
  estado: string;
  tiempo_generacion_seg: number | null;
  creado_en: string;
};

type Cliente = { id: string; nombre: string };

const MESES = ["Ene","Feb","Mar","Abr","May","Jun","Jul","Ago","Sep","Oct","Nov","Dic"];

const estadoBadge: Record<string, { className: string; label: string }> = {
  completado: { className: "badge-completado", label: "Completado" },
  procesando: { className: "badge-procesando", label: "Procesando" },
  pendiente:  { className: "badge-pendiente",  label: "Pendiente"  },
  error:      { className: "badge-error",      label: "Error"      },
};

export function HistorialPage() {
  const [reportes, setReportes] = useState<Reporte[]>([]);
  const [clientes, setClientes] = useState<Cliente[]>([]);
  const [clienteId, setClienteId] = useState<string>();
  const [mes, setMes] = useState<number>();
  const [anio, setAnio] = useState<number>();
  const [loading, setLoading] = useState(false);
  const { mostrar } = useNotifStore();

  useEffect(() => { cargar(); }, []);

  const cargar = async (params?: Record<string, unknown>) => {
    setLoading(true);
    try {
      const query = new URLSearchParams();
      if (params?.clienteId) query.set("cliente_id", String(params.clienteId));
      if (params?.mes) query.set("periodo_mes", String(params.mes));
      if (params?.anio) query.set("periodo_anio", String(params.anio));
      const r = await api.get(`/reportes?${query}`);
      setReportes(r.data);
      // Derive unique clients from results for filter
      const uniqueClientes = Array.from(
        new Map(r.data.map((rep: Reporte) => [rep.cliente.id, rep.cliente])).values()
      ) as Cliente[];
      setClientes(uniqueClientes);
    } catch {
      mostrar("Error al cargar el historial", "error");
    } finally {
      setLoading(false);
    }
  };

  const aplicarFiltros = () => cargar({ clienteId, mes, anio });

  const descargar = async (id: string) => {
    try {
      const r = await api.get(`/reportes/${id}/descargar`);
      window.open(r.data.url_descarga, "_blank");
    } catch {
      mostrar("Error al obtener el enlace de descarga", "error");
    }
  };

  const columns: ColumnsType<Reporte> = [
    {
      title: "Cliente",
      dataIndex: ["cliente", "nombre"],
      key: "cliente",
      sorter: (a, b) => a.cliente.nombre.localeCompare(b.cliente.nombre),
    },
    {
      title: "Período",
      key: "periodo",
      render: (_, r) => `${MESES[r.periodo_mes - 1]} ${r.periodo_anio}`,
      sorter: (a, b) => (a.periodo_anio * 100 + a.periodo_mes) - (b.periodo_anio * 100 + b.periodo_mes),
    },
    {
      title: "Estado",
      dataIndex: "estado",
      key: "estado",
      render: (estado) => {
        const b = estadoBadge[estado] ?? { className: "", label: estado };
        return <span className={`badge-estado ${b.className}`}>{b.label}</span>;
      },
    },
    {
      title: "Tiempo de generación",
      dataIndex: "tiempo_generacion_seg",
      key: "tiempo",
      render: (v) => v != null ? `${v.toFixed(1)}s` : "—",
    },
    {
      title: "Fecha",
      dataIndex: "creado_en",
      key: "fecha",
      render: (v) => dayjs(v).format("DD/MM/YYYY HH:mm"),
      sorter: (a, b) => dayjs(a.creado_en).unix() - dayjs(b.creado_en).unix(),
      defaultSortOrder: "descend",
    },
    {
      title: "",
      key: "acciones",
      render: (_, r) =>
        r.estado === "completado" ? (
          <Button
            type="primary"
            size="small"
            icon={<DownloadOutlined />}
            onClick={() => descargar(r.id)}
          >
            Descargar
          </Button>
        ) : null,
    },
  ];

  return (
    <div>
      <div className="page-header">
        <h1>Historial de reportes</h1>
        <p>Consulta y descarga los reportes generados de tus clientes</p>
      </div>

      {/* Filtros */}
      <div className="card" style={{ display: "flex", gap: 12, flexWrap: "wrap", alignItems: "flex-end" }}>
        <div>
          <div style={{ fontSize: 12, color: "#64748b", marginBottom: 4 }}>Cliente</div>
          <Select
            style={{ width: 200 }}
            placeholder="Todos los clientes"
            allowClear
            onChange={setClienteId}
            options={clientes.map((c) => ({ value: c.id, label: c.nombre }))}
          />
        </div>
        <div>
          <div style={{ fontSize: 12, color: "#64748b", marginBottom: 4 }}>Mes</div>
          <Select
            style={{ width: 130 }}
            placeholder="Todos"
            allowClear
            onChange={setMes}
            options={MESES.map((m, i) => ({ value: i + 1, label: m }))}
          />
        </div>
        <div>
          <div style={{ fontSize: 12, color: "#64748b", marginBottom: 4 }}>Año</div>
          <Select
            style={{ width: 100 }}
            placeholder="Todos"
            allowClear
            onChange={setAnio}
            options={[2023, 2024, 2025, 2026].map((y) => ({ value: y, label: y }))}
          />
        </div>
        <button className="btn-primary" onClick={aplicarFiltros}>
          <ReloadOutlined /> Aplicar filtros
        </button>
      </div>

      <div className="card">
        <Table
          columns={columns}
          dataSource={reportes}
          rowKey="id"
          loading={loading}
          locale={{ emptyText: <Empty description="No hay reportes para los filtros seleccionados" /> }}
          pagination={{ pageSize: 15, showTotal: (total) => `${total} reportes` }}
        />
      </div>
    </div>
  );
}
