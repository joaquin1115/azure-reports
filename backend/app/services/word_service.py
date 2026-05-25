import io
from datetime import datetime

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import patches
from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor

from app.services.analisis_service import ResultadoMetrica

COLOR_SUBTITULO = RGBColor(0x19, 0x87, 0xAF)


def _set_font(run, size_pt: int, color: RGBColor = RGBColor(0, 0, 0)):
    run.font.name = "Segoe UI Semilight"
    run._element.rPr.rFonts.set(qn("w:eastAsia"), "Segoe UI Semilight")
    run.font.size = Pt(size_pt)
    run.font.color.rgb = color


def _add_heading(doc: Document, text: str, level: int):
    p = doc.add_paragraph()
    run = p.add_run(text)
    size = 16 if level == 1 else 14 if level == 2 else 12
    _set_font(run, size, COLOR_SUBTITULO)
    run.bold = True


def _add_paragraph(doc: Document, text: str):
    p = doc.add_paragraph()
    run = p.add_run(text)
    _set_font(run, 10)


def _asignar_bordes_tabla(table):
    tbl = table._tbl
    tblPr = tbl.tblPr
    borders = OxmlElement('w:tblBorders')
    for edge in ('top', 'left', 'bottom', 'right', 'insideH', 'insideV'):
        elem = OxmlElement(f'w:{edge}')
        elem.set(qn('w:val'), 'single')
        elem.set(qn('w:sz'), '4')
        elem.set(qn('w:space'), '0')
        elem.set(qn('w:color'), 'D9D9D9')
        borders.append(elem)
    tblPr.append(borders)


def _grafico_bytes(resultado: ResultadoMetrica) -> io.BytesIO:
    fig = plt.figure(figsize=(8.2, 3.6), dpi=140)
    fig.patch.set_facecolor("white")

    # Outer Azure-like container
    outer = patches.Rectangle((0.02, 0.03), 0.96, 0.94, transform=fig.transFigure,
                              linewidth=1.0, edgecolor="#000000", facecolor="white")
    fig.patches.append(outer)
    # Pill bar
    fig.patches.append(patches.Rectangle((0.02, 0.86), 0.96, 0.11, transform=fig.transFigure,
                                         linewidth=0, facecolor="#f8f8f8"))
    # Toolbar
    fig.patches.append(patches.Rectangle((0.02, 0.75), 0.96, 0.11, transform=fig.transFigure,
                                         linewidth=0, facecolor="#fbfbfb"))
    # Legend bar
    fig.patches.append(patches.Rectangle((0.02, 0.03), 0.96, 0.10, transform=fig.transFigure,
                                         linewidth=0, facecolor="#fafafa"))

    # Chart area positioned between toolbar and legend
    ax = fig.add_axes([0.08, 0.18, 0.84, 0.53])
    valores = resultado.valores or []
    all_zero_or_empty = (not valores) or all((v or 0) == 0 for v in valores)
    linestyle = "--" if all_zero_or_empty else "-"
    x = range(len(valores))
    y = valores if valores else [0]
    x = x if valores else [0]
    ax.plot(x, y, color="#4f63c8", linewidth=1.5, linestyle=linestyle)
    ax.set_title(resultado.nombre, fontsize=9, loc="left", pad=6)
    ax.set_ylabel("%", fontsize=8)
    ax.grid(axis="y", linestyle="-", alpha=0.15, color="#000000")
    ax.tick_params(labelsize=7, colors="#666666")
    for spine in ax.spines.values():
        spine.set_visible(True)
        spine.set_linewidth(1.0)
        spine.set_edgecolor("black")

    # Header / toolbar / legend text decorations
    fig.text(0.05, 0.905, f"{resultado.nombre[:46]}...", fontsize=8, color="#222222")
    fig.text(0.05, 0.79, "Add metric   |   Line chart   |   Drill into logs", fontsize=7.5, color="#444444")
    promedio = sum(valores) / len(valores) if valores else 0
    fig.text(0.06, 0.07, "■", fontsize=10, color="#4f63c8")
    fig.text(0.08, 0.07, resultado.nombre, fontsize=7.5, color="#555555")
    fig.text(0.87, 0.07, f"{promedio:.4f}%", fontsize=8, color="#222222", ha="right")

    buf = io.BytesIO()
    plt.savefig(buf, format="png", dpi=140, bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    return buf


def _descripcion_rendimiento(cpu: ResultadoMetrica | None, memoria: ResultadoMetrica | None) -> str:
    if not cpu and not memoria:
        return "Sin datos"
    picos = False
    for m in (cpu, memoria):
        if m and ((m.maximo - m.minimo) >= 40 or m.maximo >= 85):
            picos = True
    return "Performance con picos de uso" if picos else "Performance estable"


def _buscar_metrica(metricas: list[ResultadoMetrica], aliases: list[str]) -> ResultadoMetrica | None:
    if not metricas:
        return None
    normalized = [a.lower() for a in aliases]
    for m in metricas:
        nombre = m.nombre.lower()
        if any(a in nombre for a in normalized):
            return m
    return None


def _tipo_recurso(valor) -> str:
    raw = getattr(valor, "value", valor)
    return str(raw).strip().upper()


def _fmt_rango(m: ResultadoMetrica | None) -> str:
    if not m or not m.valores:
        return "Sin datos"
    return f"{m.minimo:.2f}% - {m.maximo:.2f}%"


def _label_tipo(tipo: str) -> str:
    return {
        "VM": "Máquina Virtual",
        "DB": "Base de Datos SQL",
        "ASP": "App Service Plan",
    }.get(tipo, tipo or "Recurso")


def _metricas_por_tipo(tipo: str, metricas: list[ResultadoMetrica]) -> list[tuple[str, ResultadoMetrica | None]]:
    if tipo == "VM":
        return [
            ("Porcentaje de Uso de CPU", _buscar_metrica(metricas, ["percentage cpu", "cpupercentage", "cpu"])),
            ("Porcentaje de Uso de Memoria RAM", _buscar_metrica(metricas, ["memorypercentage", "available memory", "memory", "memoria"])),
        ]
    if tipo == "ASP":
        return [
            ("Porcentaje de Uso de CPU", _buscar_metrica(metricas, ["cpupercentage", "cpu percentage", "cpu"])),
            ("Porcentaje de Uso de Memoria", _buscar_metrica(metricas, ["memorypercentage", "memory percentage", "memory", "memoria"])),
        ]
    if tipo == "DB":
        return [
            ("Porcentaje de Uso de DTU", _buscar_metrica(metricas, ["dtu_consumption_percent", "dtu"]) or (metricas[0] if metricas else None)),
        ]
    return [(m.nombre, m) for m in metricas]


def _agregar_tabla_tipo(doc: Document, titulo: str, filas: list[dict]):
    _add_heading(doc, titulo, 2)
    tabla = doc.add_table(rows=1, cols=4)
    hdr = tabla.rows[0].cells
    hdr[0].text = "Recurso"
    hdr[1].text = "Métrica principal (Mínimo – Máximo)"
    hdr[2].text = "Métrica secundaria (Mínimo – Máximo)"
    hdr[3].text = "Detalle del rendimiento"
    for fila in filas:
        row = tabla.add_row().cells
        row[0].text = fila["recurso"]
        row[1].text = fila["principal"]
        row[2].text = fila["secundaria"]
        row[3].text = fila["detalle"]
    _asignar_bordes_tabla(tabla)


def _traducir(texto: str) -> str:
    if not texto:
        return ""
    reglas = {
        "Ensure Geo-replication is enabled for resilience": "Asegurar que la georreplicación esté habilitada para mejorar la resiliencia",
        "Use zone-supported App Service Plan": "Usar un App Service Plan con soporte de zonas",
        "Set minimum instance count for App Service to 2": "Configurar el número mínimo de instancias del App Service en 2",
        "Enable Health check for App Service": "Habilitar Health Check para App Service",
        "HighAvailability": "Alta disponibilidad",
        "Cost": "Costo",
        "OperationalExcellence": "Excelencia operacional",
        "Performance": "Rendimiento",
        "Security": "Seguridad",
    }
    out = texto
    for en, es in reglas.items():
        out = out.replace(en, es)
    return out


def _consolidar_recomendaciones(recomendaciones: list[dict]) -> list[dict]:
    consolidado = {}
    for r in recomendaciones:
        key = (r.get("categoria", ""), r.get("impacto", ""), r.get("descripcion", ""), r.get("accion", ""))
        entry = consolidado.setdefault(key, {
            "categoria": r.get("categoria", ""),
            "impacto": r.get("impacto", ""),
            "descripcion": r.get("descripcion", ""),
            "accion": r.get("accion", ""),
            "recursos": set(),
        })
        recurso = r.get("recurso") or r.get("nombre_recurso")
        if recurso:
            entry["recursos"].add(recurso.split("/")[-1])
    out = []
    for v in consolidado.values():
        v["recursos"] = sorted(v["recursos"])
        out.append(v)
    return out


def generar_word(cliente_nombre: str, periodo_mes: int, periodo_anio: int, usuario_nombre: str, recomendaciones: list[dict], resultados_por_recurso: list[dict]) -> bytes:
    doc = Document()
    _add_heading(doc, "REPORTE DE CONSUMO DE AZURE", 1)
    _add_paragraph(doc, f"Cliente: {cliente_nombre}")
    _add_paragraph(doc, f"Período: {periodo_mes:02d}/{periodo_anio}")
    _add_paragraph(doc, f"Generado: {datetime.utcnow().strftime('%d/%m/%Y %H:%M UTC')} por {usuario_nombre}")

    _add_heading(doc, "PERFORMANCE DE COMPONENTES", 1)
    filas_vm = []
    filas_asp = []
    filas_db = []
    filas_otros = []

    for r in resultados_por_recurso:
        tipo = _tipo_recurso(r.get("tipo", ""))
        metricas = r.get("metricas", [])
        metricas_tipo = _metricas_por_tipo(tipo, metricas)
        principal = metricas_tipo[0][1] if metricas_tipo else None
        secundaria = metricas_tipo[1][1] if len(metricas_tipo) > 1 else None
        fila = {
            "recurso": r.get("nombre", ""),
            "principal": _fmt_rango(principal),
            "secundaria": _fmt_rango(secundaria) if secundaria else "No aplica",
            "detalle": _descripcion_rendimiento(principal, secundaria),
        }
        if tipo == "VM":
            filas_vm.append(fila)
        elif tipo == "ASP":
            filas_asp.append(fila)
        elif tipo == "DB":
            filas_db.append(fila)
        else:
            filas_otros.append(fila)

    if filas_vm:
        _agregar_tabla_tipo(doc, "Máquinas Virtuales", filas_vm)
    if filas_asp:
        _agregar_tabla_tipo(doc, "App Service Plans", filas_asp)
    if filas_db:
        _agregar_tabla_tipo(doc, "Bases de Datos SQL", filas_db)
    if filas_otros:
        _agregar_tabla_tipo(doc, "Otros Recursos", filas_otros)

    for r in resultados_por_recurso:
        tipo = _tipo_recurso(r.get("tipo", ""))
        metricas = r.get("metricas", [])
        _add_heading(doc, f"{_label_tipo(tipo)} - {r.get('nombre','')}", 2)
        for titulo_metrica, metrica in _metricas_por_tipo(tipo, metricas):
            if not metrica:
                continue
            _add_heading(doc, titulo_metrica, 3)
            doc.add_picture(_grafico_bytes(metrica), width=Inches(6.2))

    _add_heading(doc, "RECOMENDACIONES Y SUGERENCIAS", 1)
    recs = _consolidar_recomendaciones(recomendaciones)
    if not recs:
        _add_paragraph(doc, "No se encontraron recomendaciones para el período analizado.")
    for r in recs:
        recursos = ", ".join(r["recursos"]) if r["recursos"] else "sin recursos identificados"
        impacto = _traducir(r["impacto"])
        categoria = _traducir(r["categoria"])
        descripcion = _traducir(r["descripcion"])
        accion = _traducir(r["accion"])
        texto = f"[{impacto}] {categoria}: {descripcion} Recomendación: {accion}. Recursos: {recursos}."
        _add_paragraph(doc, texto)

    for p in doc.paragraphs:
        p.alignment = WD_ALIGN_PARAGRAPH.LEFT

    out = io.BytesIO()
    doc.save(out)
    out.seek(0)
    return out.read()
