import { useState, useEffect } from "react";
import { Select, DatePicker, Button, Table, Tag, Switch, Empty } from "antd";
import { CalendarOutlined, PlusOutlined, PauseCircleOutlined } from "@ant-design/icons";
import type { ColumnsType } from "antd/es/table";
import api from "../services/apiClient";
import { useNotifStore } from "../store/store";
import dayjs, { Dayjs } from "dayjs";

type Config = { id: string; nombre: string; cliente: { nombre: string }; periodo_mes: number; periodo_anio: number };
type Programacion = { id: string; configuracion_id: string; fecha_inicio: string; frecuencia: string; proxima_ejecucion: string; activa: boolean };

export function ProgramarReportePage() {
  const [configs, setConfigs] = useState<Config[]>([]);
  const [programaciones, setProgramaciones] = useState<Programacion[]>([]);
  const [configId, setConfigId] = useState<string>();
  const [fechaInicio, setFechaInicio] = useState<Dayjs | null>(null);
  const [loading, setLoading] = useState(false);
  const { mostrar } = useNotifStore();

  useEffect(() => {
    api.get("/configuraciones?solo_guardadas=true").then((r) => setConfigs(r.data)).catch(() => {});
    cargarProgramaciones();
  }, []);

  const cargarProgramaciones = async () => {
    const r = await api.get("/programaciones");
    setProgramaciones(r.data);
  };

  const crear = async () => {
    if (!configId || !fechaInicio) return;
    setLoading(true);
    try {
      await api.post("/programaciones", {
        configuracion_id: configId,
        fecha_inicio: fechaInicio.toISOString(),
        frecuencia: "mensual",
      });
      mostrar("Programación registrada correctamente", "success");
      setConfigId(undefined);
      setFechaInicio(null);
      await cargarProgramaciones();
    } catch {
      mostrar("Error al crear la programación", "error");
    } finally {
      setLoading(false);
    }
  };

  const desactivar = async (id: string) => {
    await api.patch(`/programaciones/${id}/desactivar`);
    mostrar("Programación desactivada", "info");
    await cargarProgramaciones();
  };

  const columns: ColumnsType<Programacion> = [
    { title: "Configuración", dataIndex: "configuracion_id", key: "config",
      render: (id) => configs.find(c => c.id === id)?.nombre ?? id },
    { title: "Frecuencia", dataIndex: "frecuencia", key: "freq",
      render: (v) => <Tag color="#1987af">{v}</Tag> },
    { title: "Próxima ejecución", dataIndex: "proxima_ejecucion", key: "prox",
      render: (v) => dayjs(v).format("DD/MM/YYYY") },
    { title: "Estado", dataIndex: "activa", key: "estado",
      render: (v) => v
        ? <span className="badge-estado badge-completado">Activa</span>
        : <span className="badge-estado badge-error">Inactiva</span> },
    { title: "", key: "acc",
      render: (_, r) => r.activa
        ? <Button size="small" icon={<PauseCircleOutlined />} onClick={() => desactivar(r.id)}>Desactivar</Button>
        : null },
  ];

  return (
    <div>
      <div className="page-header">
        <h1>Programar reporte</h1>
        <p>Configura la generación automática mensual de reportes</p>
      </div>

      <div className="card">
        <div className="card-title"><span className="dot"/> Nueva programación</div>
        <div style={{ display: "flex", gap: 16, flexWrap: "wrap", alignItems: "flex-end" }}>
          <div>
            <div style={{ fontSize: 12, color: "#64748b", marginBottom: 4 }}>Configuración guardada</div>
            <Select
              style={{ width: 280 }}
              placeholder="Selecciona una configuración"
              value={configId}
              onChange={setConfigId}
              options={configs.map((c) => ({ value: c.id, label: c.nombre }))}
            />
          </div>
          <div>
            <div style={{ fontSize: 12, color: "#64748b", marginBottom: 4 }}>Fecha de inicio</div>
            <DatePicker
              value={fechaInicio}
              onChange={setFechaInicio}
              format="DD/MM/YYYY"
              placeholder="Selecciona fecha"
              disabledDate={(d) => d.isBefore(dayjs(), "day")}
            />
          </div>
          <button
            className="btn-primary"
            onClick={crear}
            disabled={!configId || !fechaInicio || loading}
          >
            <PlusOutlined /> Crear programación
          </button>
        </div>
        {configs.length === 0 && (
          <p style={{ marginTop: 12, fontSize: 13, color: "#94a3b8" }}>
            No tienes configuraciones guardadas. Genera un reporte y activa "Guardar configuración" para poder programarla.
          </p>
        )}
      </div>

      <div className="card">
        <div className="card-title"><span className="dot"/> Programaciones activas</div>
        <Table
          columns={columns}
          dataSource={programaciones}
          rowKey="id"
          locale={{ emptyText: <Empty description="No hay programaciones registradas" /> }}
          pagination={{ pageSize: 10 }}
        />
      </div>
    </div>
  );
}
