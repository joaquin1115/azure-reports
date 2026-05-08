import base64
import io
from datetime import datetime
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from weasyprint import HTML
from app.services.analisis_service import ResultadoMetrica

COLOR_PRIMARIO = "#1987af"
COLOR_SECUNDARIO = "#ffbe1e"
COLOR_FONDO = "#f8fafc"
COLOR_TEXTO = "#1e293b"


def _generar_grafico_base64(resultado: ResultadoMetrica) -> str:
    fig, ax = plt.subplots(figsize=(8, 3))
    fig.patch.set_facecolor("white")
    ax.set_facecolor("#f8fafc")

    x = range(len(resultado.valores))
    ax.fill_between(x, resultado.valores, alpha=0.15, color=COLOR_PRIMARIO)
    ax.plot(x, resultado.valores, color=COLOR_PRIMARIO, linewidth=2, marker="o", markersize=3)

    # Mark anomalies
    for a in resultado.anomalias:
        if a["fecha"] in resultado.fechas:
            idx = resultado.fechas.index(a["fecha"])
            ax.axvline(x=idx, color=COLOR_SECUNDARIO, linestyle="--", alpha=0.7, linewidth=1)
            ax.scatter([idx], [a["valor"]], color=COLOR_SECUNDARIO, zorder=5, s=60)

    ax.set_title(resultado.nombre, fontsize=10, color=COLOR_TEXTO, pad=8)
    ax.set_ylabel("%", fontsize=8, color=COLOR_TEXTO)
    ax.tick_params(colors=COLOR_TEXTO, labelsize=7)
    ax.spines[["top", "right"]].set_visible(False)
    ax.spines[["left", "bottom"]].set_color("#cbd5e1")
    ax.grid(axis="y", linestyle="--", alpha=0.4, color="#cbd5e1")

    buf = io.BytesIO()
    plt.savefig(buf, format="png", dpi=120, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    buf.seek(0)
    return base64.b64encode(buf.read()).decode("utf-8")


def _html_recomendaciones(recomendaciones: list[dict]) -> str:
    if not recomendaciones:
        return "<p class='vacio'>No se encontraron recomendaciones para el período analizado.</p>"
    filas = ""
    for r in recomendaciones:
        badge_color = COLOR_PRIMARIO if r.get("impacto") == "High" else COLOR_SECUNDARIO
        ahorro = f"${r['ahorro_mensual_usd']:.2f}/mes" if r.get("ahorro_mensual_usd") else "—"
        filas += f"""
        <tr>
          <td><span class="badge" style="background:{badge_color}">{r.get('impacto','')}</span></td>
          <td>{r.get('categoria','')}</td>
          <td class="recurso-cell">{r.get('nombre_recurso','')}</td>
          <td>{r.get('accion','')}</td>
          <td class="ahorro-cell">{ahorro}</td>
        </tr>"""
    return f"<table class='tabla-recs'><thead><tr><th>Impacto</th><th>Categoría</th><th>Recurso</th><th>Acción recomendada</th><th>Ahorro est.</th></tr></thead><tbody>{filas}</tbody></table>"


def _html_metricas(nombre_recurso: str, tipo: str, metricas: list[ResultadoMetrica]) -> str:
    secciones = ""
    for m in metricas:
        grafico_b64 = _generar_grafico_base64(m)
        obs_html = "".join(f"<li>{o}</li>" for o in m.observaciones)
        anomalias_html = ""
        if m.anomalias:
            rows = "".join(
                f"<tr><td>{a['fecha'][:10]}</td><td>{a['valor']}%</td><td>{a['z_score']}</td></tr>"
                for a in m.anomalias
            )
            anomalias_html = f"""
            <div class='anomalias'>
              <p class='sub-label'>Valores anómalos detectados</p>
              <table class='tabla-small'>
                <thead><tr><th>Fecha</th><th>Valor</th><th>Z-Score</th></tr></thead>
                <tbody>{rows}</tbody>
              </table>
            </div>"""

        secciones += f"""
        <div class='metrica-bloque'>
          <h4 class='metrica-nombre'>{m.nombre}</h4>
          <div class='metrica-stats'>
            <span><b>Promedio</b><br>{m.promedio}%</span>
            <span><b>Máximo</b><br>{m.maximo}%</span>
            <span><b>Mínimo</b><br>{m.minimo}%</span>
            <span><b>Desv. std.</b><br>{m.desviacion}%</span>
          </div>
          <img src="data:image/png;base64,{grafico_b64}" class='grafico'/>
          {anomalias_html}
          <ul class='observaciones'>{obs_html}</ul>
        </div>"""

    return f"""
    <div class='recurso-bloque'>
      <div class='recurso-header'>
        <span class='recurso-tipo'>{tipo}</span>
        <h3 class='recurso-nombre'>{nombre_recurso}</h3>
      </div>
      {secciones}
    </div>"""


def generar_pdf(
    cliente_nombre: str,
    periodo_mes: int,
    periodo_anio: int,
    usuario_nombre: str,
    recomendaciones: list[dict],
    resultados_por_recurso: list[dict],  # [{nombre, tipo, metricas: [ResultadoMetrica]}]
) -> bytes:
    meses = ["Enero","Febrero","Marzo","Abril","Mayo","Junio",
             "Julio","Agosto","Septiembre","Octubre","Noviembre","Diciembre"]
    periodo_str = f"{meses[periodo_mes - 1]} {periodo_anio}"
    fecha_gen = datetime.utcnow().strftime("%d/%m/%Y %H:%M UTC")

    total_ahorro = sum(
        r.get("ahorro_mensual_usd") or 0 for r in recomendaciones
        if r.get("ahorro_mensual_usd")
    )
    resumen_recs = len(recomendaciones)
    resumen_recursos = len(resultados_por_recurso)

    metricas_html = "".join(
        _html_metricas(r["nombre"], r["tipo"], r["metricas"])
        for r in resultados_por_recurso
    )

    html = f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8"/>
<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700&display=swap');
  * {{ margin:0; padding:0; box-sizing:border-box; }}
  body {{ font-family:'Inter',sans-serif; color:{COLOR_TEXTO}; background:#fff; font-size:10pt; }}

  /* CARATULA */
  .caratula {{
    background: linear-gradient(135deg, {COLOR_PRIMARIO} 0%, #0f5f80 100%);
    color:#fff; padding:60px 50px; min-height:220px;
    display:flex; flex-direction:column; justify-content:space-between;
  }}
  .caratula-logo {{ font-size:22pt; font-weight:700; letter-spacing:2px; }}
  .caratula-logo span {{ color:{COLOR_SECUNDARIO}; }}
  .caratula-titulo {{ font-size:16pt; font-weight:300; margin-top:16px; opacity:.9; }}
  .caratula-cliente {{ font-size:20pt; font-weight:700; margin-top:8px; }}
  .caratula-meta {{ font-size:9pt; opacity:.8; margin-top:24px; }}

  /* CONTENIDO */
  .contenido {{ padding:40px 50px; }}
  h2 {{ font-size:13pt; font-weight:700; color:{COLOR_PRIMARIO};
        border-bottom:2px solid {COLOR_SECUNDARIO};
        padding-bottom:6px; margin:32px 0 16px; }}
  h3 {{ font-size:11pt; font-weight:600; color:{COLOR_TEXTO}; margin:16px 0 8px; }}
  h4 {{ font-size:10pt; font-weight:600; color:{COLOR_PRIMARIO}; margin:12px 0 6px; }}

  /* RESUMEN EJECUTIVO */
  .resumen-grid {{
    display:grid; grid-template-columns:repeat(3,1fr); gap:16px; margin:16px 0;
  }}
  .resumen-card {{
    background:{COLOR_FONDO}; border-radius:8px; padding:16px;
    border-top:3px solid {COLOR_PRIMARIO}; text-align:center;
  }}
  .resumen-card .valor {{ font-size:22pt; font-weight:700; color:{COLOR_PRIMARIO}; }}
  .resumen-card .etiqueta {{ font-size:8.5pt; color:#64748b; margin-top:4px; }}

  /* TABLA RECOMENDACIONES */
  .tabla-recs {{ width:100%; border-collapse:collapse; margin:12px 0; font-size:9pt; }}
  .tabla-recs th {{
    background:{COLOR_PRIMARIO}; color:#fff; padding:8px 10px;
    text-align:left; font-weight:600;
  }}
  .tabla-recs td {{ padding:7px 10px; border-bottom:1px solid #e2e8f0; vertical-align:top; }}
  .tabla-recs tr:nth-child(even) td {{ background:#f8fafc; }}
  .badge {{
    display:inline-block; padding:2px 8px; border-radius:12px;
    color:#fff; font-size:8pt; font-weight:600;
  }}
  .recurso-cell {{ font-size:8pt; color:#475569; max-width:180px; word-break:break-all; }}
  .ahorro-cell {{ font-weight:600; color:#059669; white-space:nowrap; }}
  .vacio {{ color:#94a3b8; font-style:italic; text-align:center; padding:24px 0; }}

  /* RECURSOS Y MÉTRICAS */
  .recurso-bloque {{
    background:{COLOR_FONDO}; border-radius:10px; padding:20px;
    margin:16px 0; border-left:4px solid {COLOR_PRIMARIO};
  }}
  .recurso-header {{ display:flex; align-items:center; gap:10px; margin-bottom:14px; }}
  .recurso-tipo {{
    background:{COLOR_SECUNDARIO}; color:#1e293b;
    font-size:8pt; font-weight:700; padding:3px 10px; border-radius:12px;
  }}
  .recurso-nombre {{ font-size:12pt; font-weight:700; color:{COLOR_PRIMARIO}; }}
  .metrica-bloque {{ margin:14px 0; padding:14px; background:#fff; border-radius:8px; }}
  .metrica-nombre {{ font-size:10pt; font-weight:600; color:{COLOR_TEXTO}; margin-bottom:10px; }}
  .metrica-stats {{
    display:grid; grid-template-columns:repeat(4,1fr);
    gap:10px; margin:10px 0; text-align:center;
  }}
  .metrica-stats span {{
    background:{COLOR_FONDO}; padding:8px; border-radius:6px;
    font-size:9pt; color:{COLOR_TEXTO};
  }}
  .metrica-stats b {{ display:block; font-size:8pt; color:#64748b; margin-bottom:4px; }}
  .grafico {{ width:100%; max-height:180px; margin:10px 0; }}
  .observaciones {{ margin:10px 0 0 16px; font-size:9pt; color:#334155; }}
  .observaciones li {{ margin-bottom:4px; }}
  .anomalias {{ margin:8px 0; }}
  .sub-label {{ font-size:8.5pt; font-weight:600; color:{COLOR_SECUNDARIO}; margin-bottom:4px; }}
  .tabla-small {{ width:auto; border-collapse:collapse; font-size:8.5pt; }}
  .tabla-small th {{
    background:{COLOR_SECUNDARIO}; color:#1e293b; padding:4px 10px; font-weight:600;
  }}
  .tabla-small td {{ padding:3px 10px; border-bottom:1px solid #e2e8f0; }}

  /* PAGE BREAK */
  .page-break {{ page-break-before:always; }}
</style>
</head>
<body>

<div class="caratula">
  <div>
    <div class="caratula-logo">G<span>&</span>S</div>
    <div class="caratula-titulo">Reporte de Consumo de Azure</div>
    <div class="caratula-cliente">{cliente_nombre}</div>
  </div>
  <div class="caratula-meta">
    Período: {periodo_str} &nbsp;|&nbsp; Generado: {fecha_gen} &nbsp;|&nbsp; Especialista: {usuario_nombre}
  </div>
</div>

<div class="contenido">

  <h2>Resumen ejecutivo</h2>
  <div class="resumen-grid">
    <div class="resumen-card">
      <div class="valor">{resumen_recs}</div>
      <div class="etiqueta">Recomendaciones identificadas</div>
    </div>
    <div class="resumen-card">
      <div class="valor">{resumen_recursos}</div>
      <div class="etiqueta">Recursos analizados</div>
    </div>
    <div class="resumen-card">
      <div class="valor" style="color:#059669">${total_ahorro:,.0f}</div>
      <div class="etiqueta">Ahorro potencial estimado / mes (USD)</div>
    </div>
  </div>

  <h2 class="page-break">Recomendaciones de Azure Advisor</h2>
  {_html_recomendaciones(recomendaciones)}

  <h2 class="page-break">Análisis de métricas de recursos</h2>
  {metricas_html}

</div>
</body>
</html>"""

    return HTML(string=html).write_pdf()
