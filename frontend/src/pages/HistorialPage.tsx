import { useState, useEffect } from "react";
import { Table, Select, Button, Tag, Empty, Descriptions, Alert } from "antd";
import { DownloadOutlined, ReloadOutlined } from "@ant-design/icons";
import type { ColumnsType } from "antd/es/table";
import api from "../services/apiClient";
import { useNotifStore } from "../store/store";
import dayjs from "dayjs";

type RecursoReporte = { id: string; azure_resource_id: string; nombre: string };
type Reporte = {
  id: string;
  cliente: { id: string; nombre: string };
  periodo_mes: number;
  periodo_anio: number;
  estado: string;
  tipo_recomendacion: string;
  recurrencia: string;
  inicio_generacion: string | null;
  fin_generacion: string | null;
  tiempo_generacion_seg: number | null;
  error_mensaje: string | null;
  recursos: RecursoReporte[];
  creado_en: string;
};

type Cliente = { id: string; nombre: string };

const MESES = ["Ene","Feb","Mar","Abr","May","Jun","Jul","Ago","Sep","Oct","Nov","Dic"];
const estadoBadge: Record<string, { className: string; label: string }> = {
  Completado: { className: "badge-completado", label: "Completado" },
  "En proceso": { className: "badge-procesando", label: "En proceso" },
  Pendiente: { className: "badge-pendiente", label: "Pendiente" },
  Error: { className: "badge-error", label: "Error" },
};

const fmt = (v: string | null) => v ? dayjs(v).format("DD/MM/YYYY HH:mm") : "—";

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
      const uniqueClientes = Array.from(new Map(r.data.map((rep: Reporte) => [rep.cliente.id, rep.cliente])).values()) as Cliente[];
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
    { title: "Cliente", dataIndex: ["cliente", "nombre"], key: "cliente", sorter: (a, b) => a.cliente.nombre.localeCompare(b.cliente.nombre) },
    { title: "Período", key: "periodo", render: (_, r) => `${MESES[r.periodo_mes - 1]} ${r.periodo_anio}`, sorter: (a, b) => (a.periodo_anio * 100 + a.periodo_mes) - (b.periodo_anio * 100 + b.periodo_mes) },
    { title: "Recomendaciones", dataIndex: "tipo_recomendacion", key: "tipo", render: (v) => <Tag color="#1987af">{v}</Tag> },
    { title: "Estado", dataIndex: "estado", key: "estado", render: (estado) => { const b = estadoBadge[estado] ?? { className: "", label: estado }; return <span className={`badge-estado ${b.className}`}>{b.label}</span>; } },
    { title: "Inicio", dataIndex: "inicio_generacion", key: "inicio", render: fmt, sorter: (a, b) => dayjs(a.inicio_generacion ?? a.creado_en).unix() - dayjs(b.inicio_generacion ?? b.creado_en).unix(), defaultSortOrder: "descend" },
    { title: "Fin", dataIndex: "fin_generacion", key: "fin", render: fmt },
    { title: "", key: "acciones", render: (_, r) => r.estado === "Completado" ? <Button type="primary" size="small" icon={<DownloadOutlined />} onClick={() => descargar(r.id)}>Descargar</Button> : null },
  ];

  return (
    <div>
      <div className="page-header">
        <h1>Historial de reportes</h1>
        <p>Consulta el detalle operativo de cada reporte generado.</p>
      </div>

      <div className="card" style={{ display: "flex", gap: 12, flexWrap: "wrap", alignItems: "flex-end" }}>
        <div><div style={{ fontSize: 12, color: "#64748b", marginBottom: 4 }}>Cliente</div><Select style={{ width: 200 }} placeholder="Todos los clientes" allowClear onChange={setClienteId} options={clientes.map((c) => ({ value: c.id, label: c.nombre }))} /></div>
        <div><div style={{ fontSize: 12, color: "#64748b", marginBottom: 4 }}>Mes</div><Select style={{ width: 130 }} placeholder="Todos" allowClear onChange={setMes} options={MESES.map((m, i) => ({ value: i + 1, label: m }))} /></div>
        <div><div style={{ fontSize: 12, color: "#64748b", marginBottom: 4 }}>Año</div><Select style={{ width: 100 }} placeholder="Todos" allowClear onChange={setAnio} options={[2023, 2024, 2025, 2026].map((y) => ({ value: y, label: y }))} /></div>
        <button className="btn-primary" onClick={aplicarFiltros}><ReloadOutlined /> Aplicar filtros</button>
      </div>

      <div className="card">
        <Table
          columns={columns}
          dataSource={reportes}
          rowKey="id"
          loading={loading}
          expandable={{ expandedRowRender: (r) => (
            <div style={{ padding: 8 }}>
              <Descriptions size="small" column={2} bordered>
                <Descriptions.Item label="Recurrencia">{r.recurrencia}</Descriptions.Item>
                <Descriptions.Item label="Tiempo">{r.tiempo_generacion_seg != null ? `${r.tiempo_generacion_seg.toFixed(1)}s` : "—"}</Descriptions.Item>
                <Descriptions.Item label="Inicio">{fmt(r.inicio_generacion)}</Descriptions.Item>
                <Descriptions.Item label="Fin">{fmt(r.fin_generacion)}</Descriptions.Item>
                <Descriptions.Item label="Recursos" span={2}>{r.recursos.length ? r.recursos.map((x) => <Tag key={x.id}>{x.nombre}</Tag>) : "—"}</Descriptions.Item>
              </Descriptions>
              {r.error_mensaje && <Alert type="error" message="Error de generación" description={r.error_mensaje} style={{ marginTop: 12 }} />}
            </div>
          ) }}
          locale={{ emptyText: <Empty description="No hay reportes para los filtros seleccionados" /> }}
          pagination={{ pageSize: 15, showTotal: (total) => `${total} reportes` }}
        />
      </div>
    </div>
  );
}
