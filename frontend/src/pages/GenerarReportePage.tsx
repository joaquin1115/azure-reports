import { useState, useEffect } from "react";
import { Steps, Select, Checkbox, Radio, Button, Spin, Tag, Alert } from "antd";
import { FileTextOutlined, CloudOutlined, SendOutlined, SaveOutlined } from "@ant-design/icons";
import api from "../services/apiClient";
import { suscribirReporte } from "../services/sseService";
import { useNotifStore } from "../store/store";
import { useMsal } from "@azure/msal-react";
import { loginRequest } from "../services/authConfig";
import dayjs from "dayjs";

type Recurso = { resource_id: string; nombre: string; tipo: string; };
type Cliente = { id: string; nombre: string; };

const MESES = ["Enero","Febrero","Marzo","Abril","Mayo","Junio",
                "Julio","Agosto","Septiembre","Octubre","Noviembre","Diciembre"];

export function GenerarReportePage() {
  const [paso, setPaso] = useState(0);
  const [clientes, setClientes] = useState<Cliente[]>([]);
  const [clienteId, setClienteId] = useState<string>();
  const [recursos, setRecursos] = useState<Recurso[]>([]);
  const [recursosSeleccionados, setRecursosSeleccionados] = useState<string[]>([]);
  const [mes, setMes] = useState(dayjs().subtract(1, "month").month() + 1);
  const [anio, setAnio] = useState(dayjs().subtract(1, "month").year());
  const [gravedad, setGravedad] = useState<"alta" | "media" | "ambas">("ambas");
  const [guardar, setGuardar] = useState(false);
  const [nombreConfig, setNombreConfig] = useState("");
  const [loadingRecursos, setLoadingRecursos] = useState(false);
  const [generando, setGenerando] = useState(false);
  const [reporteId, setReporteId] = useState<string>();
  const [tiempoGen, setTiempoGen] = useState<number>();
  const [etapasCompletadas, setEtapasCompletadas] = useState<string[]>([]);
  const [etapaActual, setEtapaActual] = useState<string>();

  const { mostrar } = useNotifStore();
  const { instance, accounts } = useMsal();

  useEffect(() => {
    api
      .get("/clientes")
      .then((r) => {
        console.log("DEBUG /clientes response:", r.data);
        console.log("DEBUG type:", typeof r.data);
        console.log("DEBUG isArray:", Array.isArray(r.data));

        setClientes(r.data);
      })
      .catch((e) => {
        console.error("ERROR cargando clientes:", e);
      });
  }, []);

  const cargarRecursos = async (id: string) => {
    setClienteId(id);
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

  const getToken = async () => {
    const result = await instance.acquireTokenSilent({ ...loginRequest, account: accounts[0] });
    return result.accessToken;
  };

  const iniciarGeneracion = async () => {
    setGenerando(true);
    setTiempoGen(undefined);
    setEtapasCompletadas([]);
    setEtapaActual(undefined);
    try {
      // 1. Create or save configuration
      const configPayload = {
        cliente_id: clienteId,
        nombre: guardar ? nombreConfig : `Config ${mes}/${anio}`,
        periodo_mes: mes,
        periodo_anio: anio,
        gravedad,
        guardada: guardar,
        recursos: recursosSeleccionados.map((rid) => {
          const rec = recursos.find((r) => r.resource_id === rid)!;
          return { resource_id_azure: rid, nombre: rec.nombre, tipo: rec.tipo };
        }),
      };
      const configResp = await api.post("/configuraciones", configPayload);
      const configId = configResp.data.id;

      // 2. Trigger generation
      const genResp = await api.post("/reportes", { configuracion_id: configId });
      const rid = genResp.data.reporte_id;
      setReporteId(rid);

      mostrar("Generación iniciada. Te notificaremos cuando esté lista.", "info");

      // 3. Subscribe to SSE
      const token = await getToken();
      const unsub = suscribirReporte(rid, (evento) => {
        if (evento.evento === "progreso" && evento.etapa) {
          if (evento.estado_etapa === "iniciada") {
            setEtapaActual(evento.etapa);
          } else if (evento.estado_etapa === "completada") {
            setEtapaActual((prev) => (prev === evento.etapa ? undefined : prev));
            setEtapasCompletadas((prev) => (
              prev.includes(evento.etapa as string) ? prev : [...prev, evento.etapa as string]
            ));
          }
        } else if (evento.evento === "completado") {
          setTiempoGen(evento.tiempo_seg);
          setGenerando(false);
          setEtapaActual(undefined);
          mostrar(`✅ Reporte generado en ${evento.tiempo_seg?.toFixed(1)}s`, "success");
          unsub();
        } else if (evento.evento === "error") {
          setGenerando(false);
          mostrar(`❌ Error al generar el reporte: ${evento.mensaje}`, "error");
          unsub();
        }
      }, token);

    } catch {
      setGenerando(false);
      mostrar("Error al iniciar la generación del reporte", "error");
    }
  };

  const descargar = async () => {
    if (!reporteId) return;
    const r = await api.get(`/reportes/${reporteId}/descargar`);
    window.open(r.data.url_descarga, "_blank");
  };

  const tipoColor: Record<string, string> = { VM: "#1987af", DB: "#7c3aed", ASP: "#d97706" };
  const etapas = [
    { key: "analisis_metricas", label: "Análisis de métricas" },
    { key: "redaccion_recomendaciones", label: "Redacción de recomendaciones" },
  ];

  return (
    <div>
      <div className="page-header">
        <h1>Generar reporte</h1>
        <p>Configura y genera el reporte de consumo de Azure para un cliente</p>
      </div>

      <Steps
        current={paso}
        style={{ marginBottom: 28 }}
        items={[
          { title: "Cliente y recursos", icon: <CloudOutlined /> },
          { title: "Período y opciones",  icon: <FileTextOutlined /> },
          { title: "Generar",             icon: <SendOutlined /> },
        ]}
      />

      {/* PASO 0 */}
      {paso === 0 && (
        <div className="card">
          <div className="card-title"><span className="dot"/> Seleccionar cliente</div>
          <Select
            style={{ width: "100%", marginBottom: 20 }}
            placeholder="Selecciona un cliente"
            onChange={cargarRecursos}
            options={clientes.map((c) => ({ value: c.id, label: c.nombre }))}
          />
          {loadingRecursos && <Spin />}
          {recursos.length > 0 && (
            <>
              <div className="card-title" style={{ marginTop: 16 }}>
                <span className="dot"/> Seleccionar recursos a analizar
              </div>
              <Checkbox.Group
                style={{ display: "flex", flexDirection: "column", gap: 10 }}
                onChange={(vals) => setRecursosSeleccionados(vals as string[])}
              >
                {recursos.map((r) => (
                  <Checkbox key={r.resource_id} value={r.resource_id}>
                    <Tag color={tipoColor[r.tipo]} style={{ marginRight: 6 }}>{r.tipo}</Tag>
                    {r.nombre}
                  </Checkbox>
                ))}
              </Checkbox.Group>
            </>
          )}
          <div style={{ marginTop: 24, display: "flex", justifyContent: "flex-end" }}>
            <button
              className="btn-primary"
              disabled={!clienteId || recursosSeleccionados.length === 0}
              onClick={() => setPaso(1)}
            >
              Siguiente →
            </button>
          </div>
        </div>
      )}

      {/* PASO 1 */}
      {paso === 1 && (
        <div className="card">
          <div className="card-title"><span className="dot"/> Período del reporte</div>
          <div style={{ display: "flex", gap: 16, marginBottom: 20 }}>
            <Select
              style={{ width: 160 }}
              value={mes}
              onChange={setMes}
              options={MESES.map((m, i) => ({ value: i + 1, label: m }))}
            />
            <Select
              style={{ width: 100 }}
              value={anio}
              onChange={setAnio}
              options={[2023, 2024, 2025, 2026].map((y) => ({ value: y, label: y }))}
            />
          </div>

          <div className="card-title"><span className="dot"/> Nivel de gravedad de recomendaciones</div>
          <Radio.Group value={gravedad} onChange={(e) => setGravedad(e.target.value)} style={{ marginBottom: 20 }}>
            <Radio value="alta">Solo alta</Radio>
            <Radio value="media">Solo media</Radio>
            <Radio value="ambas">Alta y media</Radio>
          </Radio.Group>

          <div className="card-title"><span className="dot"/> Guardar configuración</div>
          <Checkbox
            checked={guardar}
            onChange={(e) => setGuardar(e.target.checked)}
            style={{ marginBottom: guardar ? 12 : 0 }}
          >
            Guardar esta configuración para uso futuro
          </Checkbox>
          {guardar && (
            <input
              className="ant-input"
              placeholder="Nombre de la configuración"
              value={nombreConfig}
              onChange={(e) => setNombreConfig(e.target.value)}
              style={{
                display: "block", marginTop: 8, padding: "6px 12px",
                border: "1px solid #d9d9d9", borderRadius: 8, width: "100%", fontFamily: "inherit",
              }}
            />
          )}

          <div style={{ marginTop: 24, display: "flex", gap: 10, justifyContent: "flex-end" }}>
            <button className="btn-secondary" onClick={() => setPaso(0)}>← Anterior</button>
            <button className="btn-primary" onClick={() => setPaso(2)}>Siguiente →</button>
          </div>
        </div>
      )}

      {/* PASO 2 */}
      {paso === 2 && (
        <div className="card">
          <div className="card-title"><span className="dot"/> Resumen de la solicitud</div>
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13.5, marginBottom: 20 }}>
            <tbody>
              {[
                ["Cliente", clientes.find(c => c.id === clienteId)?.nombre],
                ["Recursos seleccionados", recursosSeleccionados.length],
                ["Período", `${MESES[mes - 1]} ${anio}`],
                ["Nivel de gravedad", gravedad],
                ["Guardar configuración", guardar ? `Sí — "${nombreConfig}"` : "No"],
              ].map(([k, v]) => (
                <tr key={String(k)}>
                  <td style={{ padding: "8px 0", color: "#64748b", width: 200, fontWeight: 500 }}>{k}</td>
                  <td style={{ padding: "8px 0", fontWeight: 600 }}>{String(v)}</td>
                </tr>
              ))}
            </tbody>
          </table>

          {generando && (
            <Alert
              type="info"
              message="Generando reporte..."
              description={
                <div style={{ marginTop: 6 }}>
                  {etapas.map((etapa) => (
                    <div key={etapa.key} style={{ marginBottom: 4 }}>
                      {etapasCompletadas.includes(etapa.key) ? "✅" : etapaActual === etapa.key ? "🔄" : "⏳"} {etapa.label}
                    </div>
                  ))}
                </div>
              }
              showIcon
              style={{ marginBottom: 16 }}
              icon={<Spin size="small" />}
            />
          )}

          {tiempoGen !== undefined && (
            <Alert
              type="success"
              message={`Reporte generado en ${tiempoGen.toFixed(1)} segundos`}
              showIcon
              action={
                <Button size="small" type="primary" onClick={descargar}>
                  Descargar DOCX
                </Button>
              }
              style={{ marginBottom: 16 }}
            />
          )}

          <div style={{ display: "flex", gap: 10, justifyContent: "flex-end" }}>
            <button className="btn-secondary" onClick={() => setPaso(1)} disabled={generando}>
              ← Anterior
            </button>
            <button
              className="btn-primary"
              onClick={iniciarGeneracion}
              disabled={generando || tiempoGen !== undefined}
            >
              <SendOutlined /> {generando ? "Generando..." : "Generar reporte"}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
