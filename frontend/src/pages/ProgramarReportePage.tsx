import { useState, useEffect } from "react";
import { Select, DatePicker, Button, Table, Tag, Empty, Checkbox, Radio, Spin } from "antd";
import { CalendarOutlined, PlusOutlined, PauseCircleOutlined } from "@ant-design/icons";
import type { ColumnsType } from "antd/es/table";
import api from "../services/apiClient";
import { useNotifStore } from "../store/store";
import dayjs, { Dayjs } from "dayjs";

type Cliente = { id: string; nombre: string };
type Recurso = { resource_id: string; nombre: string; tipo: string };
type RecursoProgramado = { id: string; azure_resource_id: string; nombre: string };
type Programacion = {
  id: string;
  cliente: Cliente;
  tipo_recomendacion: string;
  frecuencia: string;
  proxima_ejecucion: string;
  activa: boolean;
  recursos: RecursoProgramado[];
};

export function ProgramarReportePage() {
  const [clientes, setClientes] = useState<Cliente[]>([]);
  const [programaciones, setProgramaciones] = useState<Programacion[]>([]);
  const [clienteId, setClienteId] = useState<string>();
  const [recursos, setRecursos] = useState<Recurso[]>([]);
  const [recursosSeleccionados, setRecursosSeleccionados] = useState<string[]>([]);
  const [gravedad, setGravedad] = useState<"alta" | "media" | "ambas">("ambas");
  const [fechaInicio, setFechaInicio] = useState<Dayjs | null>(null);
  const [loading, setLoading] = useState(false);
  const [loadingRecursos, setLoadingRecursos] = useState(false);
  const { mostrar } = useNotifStore();

  useEffect(() => {
    api.get("/clientes").then((r) => setClientes(r.data)).catch(() => {});
    cargarProgramaciones();
  }, []);

  const cargarProgramaciones = async () => {
    const r = await api.get("/programaciones");
    setProgramaciones(r.data);
  };

  const cargarRecursos = async (id: string) => {
    setClienteId(id);
    setRecursosSeleccionados([]);
    setLoadingRecursos(true);
    try {
      const r = await api.get(`/clientes/${id}/recursos`);
      setRecursos(r.data);
    } catch {
      mostrar("No se pudieron obtener los recursos de Azure", "error");
    } finally {
      setLoadingRecursos(false);
    }
  };

  const crear = async () => {
    if (!clienteId || recursosSeleccionados.length === 0 || !fechaInicio) return;
    setLoading(true);
    try {
      await api.post("/programaciones", {
        cliente_id: clienteId,
        fecha_inicio: fechaInicio.toISOString(),
        frecuencia: "Mensual",
        gravedad,
        recursos: recursosSeleccionados.map((rid) => {
          const rec = recursos.find((r) => r.resource_id === rid)!;
          return { resource_id_azure: rid, nombre: rec.nombre, tipo: rec.tipo };
        }),
      });
      mostrar("Programación registrada correctamente", "success");
      setClienteId(undefined);
      setRecursos([]);
      setRecursosSeleccionados([]);
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
    { title: "Cliente", dataIndex: ["cliente", "nombre"], key: "cliente" },
    { title: "Recomendaciones", dataIndex: "tipo_recomendacion", key: "tipo", render: (v) => <Tag color="#1987af">{v}</Tag> },
    { title: "Recursos", dataIndex: "recursos", key: "recursos", render: (rs: RecursoProgramado[]) => rs.length },
    { title: "Frecuencia", dataIndex: "frecuencia", key: "freq", render: (v) => <Tag color="#64748b">{v}</Tag> },
    { title: "Próxima ejecución", dataIndex: "proxima_ejecucion", key: "prox", render: (v) => dayjs(v).format("DD/MM/YYYY") },
    { title: "Estado", dataIndex: "activa", key: "estado", render: (v) => v ? <span className="badge-estado badge-completado">Activa</span> : <span className="badge-estado badge-error">Inactiva</span> },
    { title: "", key: "acc", render: (_, r) => r.activa ? <Button size="small" icon={<PauseCircleOutlined />} onClick={() => desactivar(r.id)}>Desactivar</Button> : null },
  ];

  return (
    <div>
      <div className="page-header">
        <h1>Programar reporte</h1>
        <p>Selecciona cliente, recursos y alcance de recomendaciones para una ejecución mensual automática.</p>
      </div>

      <div className="card">
        <div className="card-title"><span className="dot"/> Nueva programación</div>
        <div style={{ display: "grid", gap: 16 }}>
          <Select style={{ width: "100%" }} placeholder="Selecciona un cliente" value={clienteId} onChange={cargarRecursos} options={clientes.map((c) => ({ value: c.id, label: c.nombre }))} />
          {loadingRecursos && <Spin />}
          {recursos.length > 0 && (
            <Checkbox.Group style={{ display: "flex", flexDirection: "column", gap: 8 }} value={recursosSeleccionados} onChange={(vals) => setRecursosSeleccionados(vals as string[])}>
              {recursos.map((r) => <Checkbox key={r.resource_id} value={r.resource_id}><Tag>{r.tipo}</Tag>{r.nombre}</Checkbox>)}
            </Checkbox.Group>
          )}
          <Radio.Group value={gravedad} onChange={(e) => setGravedad(e.target.value)}>
            <Radio value="alta">Críticas: solo alta</Radio>
            <Radio value="media">Prioritarias: alta y media</Radio>
            <Radio value="ambas">Todas: alta, media y baja</Radio>
          </Radio.Group>
          <DatePicker value={fechaInicio} onChange={setFechaInicio} format="DD/MM/YYYY" placeholder="Fecha de inicio" disabledDate={(d) => d.isBefore(dayjs(), "day")} />
          <button className="btn-primary" onClick={crear} disabled={!clienteId || recursosSeleccionados.length === 0 || !fechaInicio || loading}>
            <PlusOutlined /> Crear programación
          </button>
        </div>
      </div>

      <div className="card">
        <div className="card-title"><span className="dot"/> Programaciones</div>
        <Table columns={columns} dataSource={programaciones} rowKey="id" locale={{ emptyText: <Empty description="No hay programaciones registradas" /> }} pagination={{ pageSize: 10 }} />
      </div>
    </div>
  );
}
