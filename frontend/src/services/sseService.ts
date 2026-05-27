export type SSEEvento = {
  evento: "progreso" | "completado" | "error" | "ping";
  reporte_id?: string;
  tiempo_seg?: number;
  mensaje?: string;
  etapa?: "analisis_metricas" | "redaccion_recomendaciones";
};

export function suscribirReporte(
  reporteId: string,
  onEvento: (e: SSEEvento) => void,
  token: string,
): () => void {
  const url = `${import.meta.env.VITE_API_URL ?? "http://localhost:8000/api"}/reportes/sse/${reporteId}`;
  const source = new EventSource(`${url}?token=${encodeURIComponent(token)}`);

  source.onmessage = (event) => {
    try {
      const data: SSEEvento = JSON.parse(event.data);
      onEvento(data);
      if (data.evento === "completado" || data.evento === "error") {
        source.close();
      }
    } catch {
      // malformed message, ignore
    }
  };

  source.onerror = () => {
    source.close();
  };

  return () => source.close();
}
