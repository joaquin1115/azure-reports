import io
from datetime import datetime

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
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
    fig, ax = plt.subplots(figsize=(7.5, 2.4))
    ax.plot(range(len(resultado.valores)), resultado.valores, color="#1987af", linewidth=2)
    ax.set_title(resultado.nombre, fontsize=9)
    ax.set_ylabel("%", fontsize=8)
    ax.grid(axis="y", linestyle="--", alpha=0.4)
    ax.tick_params(labelsize=7)
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


def _buscar_metrica(metricas: list[ResultadoMetrica], palabras: list[str]) -> ResultadoMetrica | None:
    for m in metricas:
        nombre = m.nombre.lower()
        if all(p in nombre for p in palabras):
            return m
    return None


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
    tabla = doc.add_table(rows=1, cols=4)
    hdr = tabla.rows[0].cells
    hdr[0].text = "Máquinas Virtuales"
    hdr[1].text = "Performance de CPU (Mínimo – Máximo)"
    hdr[2].text = "Performance de Memoria (Mínimo – Máximo)"
    hdr[3].text = "Detalle del rendimiento"

    for r in resultados_por_recurso:
        if str(r.get("tipo", "")).upper() != "VM":
            continue
        metricas = r.get("metricas", [])
        cpu = _buscar_metrica(metricas, ["cpu"]) or _buscar_metrica(metricas, ["percentage", "cpu"])
        mem = _buscar_metrica(metricas, ["memory"]) or _buscar_metrica(metricas, ["memoria"])
        row = tabla.add_row().cells
        row[0].text = r.get("nombre", "")
        row[1].text = f"{cpu.minimo if cpu else 0}% - {cpu.maximo if cpu else 0}%"
        row[2].text = f"{mem.minimo if mem else 0}% - {mem.maximo if mem else 0}%"
        row[3].text = _descripcion_rendimiento(cpu, mem)

    _asignar_bordes_tabla(tabla)

    for r in resultados_por_recurso:
        tipo = str(r.get("tipo", "")).upper()
        metricas = r.get("metricas", [])
        if tipo == "DB":
            _add_heading(doc, "Porcentaje de Uso de DTU", 2)
            _add_heading(doc, f"Base de datos SQL - {r.get('nombre','')}", 3)
            dtu = _buscar_metrica(metricas, ["dtu"]) or (metricas[0] if metricas else None)
            if dtu:
                doc.add_picture(_grafico_bytes(dtu), width=Inches(6.2))
        elif tipo == "VM":
            _add_heading(doc, f"Máquina Virtual - {r.get('nombre','')}", 2)
            cpu = _buscar_metrica(metricas, ["cpu"])
            mem = _buscar_metrica(metricas, ["memory"]) or _buscar_metrica(metricas, ["memoria"])
            if cpu:
                _add_heading(doc, "Porcentaje de Uso de CPU", 3)
                doc.add_picture(_grafico_bytes(cpu), width=Inches(6.2))
            if mem:
                _add_heading(doc, "Porcentaje de Uso de Memoria RAM", 3)
                doc.add_picture(_grafico_bytes(mem), width=Inches(6.2))

    _add_heading(doc, "RECOMENDACIONES Y SUGERENCIAS", 1)
    recs = _consolidar_recomendaciones(recomendaciones)
    if not recs:
        _add_paragraph(doc, "No se encontraron recomendaciones para el período analizado.")
    for r in recs:
        recursos = ", ".join(r["recursos"]) if r["recursos"] else "sin recursos identificados"
        texto = f"[{r['impacto']}] {r['categoria']}: {r['descripcion']} Recomendación: {r['accion']}. Recursos: {recursos}."
        _add_paragraph(doc, texto)

    for p in doc.paragraphs:
        p.alignment = WD_ALIGN_PARAGRAPH.LEFT

    out = io.BytesIO()
    doc.save(out)
    out.seek(0)
    return out.read()
