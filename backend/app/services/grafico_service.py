import io
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.image as mpimg
import numpy as np
from matplotlib.gridspec import GridSpec
from matplotlib.offsetbox import OffsetImage, AnnotationBbox
from matplotlib.patches import Rectangle

from app.services.analisis_service import ResultadoMetrica


def generar_grafico_bytes(
    resultado: ResultadoMetrica,
    tipo_recurso: str
) -> bytes:

    valores = resultado.valores or []

    fig = plt.figure(figsize=(8.4, 4.1), dpi=150)
    fig.patch.set_facecolor("white")

    gs = GridSpec(
        3,
        1,
        height_ratios=[0.14, 0.72, 0.14],
        hspace=0
    )

    ax_header = fig.add_subplot(gs[0])
    ax_chart = fig.add_subplot(gs[1])
    ax_legend = fig.add_subplot(gs[2])

    for ax in [ax_header, ax_legend]:
        ax.set_xticks([])
        ax.set_yticks([])
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.axis("off")

    # =========================================================
    # CONTENEDOR EXTERIOR
    # =========================================================

    border = Rectangle(
        (0.01, 0.01),
        0.98,
        0.98,
        transform=fig.transFigure,
        fill=False,
        linewidth=0.7,
        edgecolor="#d8d8d8"
    )

    fig.patches.append(border)

    # =========================================================
    # HEADER
    # =========================================================

    ax_header.add_patch(
        Rectangle(
            (0, 0),
            1,
            1,
            facecolor="#ffffff",
            edgecolor="#eaeaea",
            linewidth=0.6
        )
    )

    # =========================================================
    # ICONO DESDE BACKEND
    # =========================================================

    BASE_ICONOS = Path("assets/azure_icons")

    mapa_iconos = {
        "VM": "virtual-machine.png",
        "DB": "sql-database.png",
        "ASP": "app-service-plans.png",
    }

    icono = mapa_iconos.get(tipo_recurso.upper(), "default.png")

    ruta_icono = BASE_ICONOS / icono

    if ruta_icono.exists():

        img = mpimg.imread(ruta_icono)

        imagebox = OffsetImage(img, zoom=0.02)

        ab = AnnotationBbox(
            imagebox,
            (0.035, 0.5),
            frameon=False,
            xycoords=ax_header.transAxes
        )

        ax_header.add_artist(ab)

    nombre_recurso = getattr(resultado, "recurso", None)

    if nombre_recurso:
        titulo = f"{resultado.nombre} - {nombre_recurso}"
    else:
        titulo = resultado.nombre

    titulo = titulo[:85]

    if len(titulo) > 85:
        titulo += "..."

    ax_header.text(
        0.048,
        0.5,
        titulo,
        fontsize=8,
        va="center",
        color="#222222"
    )

    # =========================================================
    # CHART
    # =========================================================

    ax_chart.set_facecolor("white")

    x = np.arange(len(valores))

    if not valores:
        valores = [0, 0]
        x = np.arange(len(valores))

    valores_np = np.array(valores, dtype=float)

    solid_y = np.where(np.isnan(valores_np), np.nan, valores_np)

    if np.all(np.isnan(valores_np)):
        missing = np.zeros_like(valores_np)
    else:
        mean_val = np.nanmean(valores_np)
        missing = np.where(np.isnan(valores_np), mean_val, np.nan)

    # línea principal
    ax_chart.plot(
        x,
        solid_y,
        color="#4f63c8",
        linewidth=1.6,
        solid_capstyle="round",
        zorder=3
    )

    # segmentos faltantes
    ax_chart.plot(
        x,
        missing,
        color="#4f63c8",
        linewidth=1.4,
        linestyle=(0, (4, 4)),
        alpha=0.7,
        zorder=2
    )

    # área suave
    if not np.all(np.isnan(solid_y)):
        ax_chart.fill_between(
            x,
            solid_y,
            alpha=0.06,
            color="#4f63c8",
            zorder=1
        )

    # grid
    ax_chart.grid(
        axis="y",
        color=(0, 0, 0, 0.018),
        linewidth=0.3
    )

    # estilos
    ax_chart.tick_params(
        axis="x",
        labelsize=7,
        colors="#666666"
    )

    ax_chart.tick_params(
        axis="y",
        labelsize=7,
        colors="#666666"
    )

    ax_chart.spines["top"].set_visible(False)
    ax_chart.spines["right"].set_visible(False)

    ax_chart.spines["left"].set_color("#dddddd")
    ax_chart.spines["bottom"].set_color("#dddddd")

    ax_chart.set_ylabel(
        "%",
        fontsize=8,
        color="#666666"
    )

    if len(valores_np) > 0:

        vmax = np.nanmax(valores_np)

        if np.isnan(vmax) or vmax <= 0:
            vmax = 1

        ax_chart.set_ylim(0, vmax * 1.2)

    ax_chart.set_xlim(0, max(len(x) - 1, 1))

    ax_chart.margins(x=0)

    # =========================================================
    # LEYENDA
    # =========================================================

    ax_legend.add_patch(
        Rectangle(
            (0, 0),
            1,
            1,
            facecolor="#ffffff",
            edgecolor="#eaeaea",
            linewidth=0.6
        )
    )

    ax_legend.add_patch(
        Rectangle(
            (0.03, 0.42),
            0.012,
            0.18,
            facecolor="#4f63c8",
            edgecolor="#4f63c8"
        )
    )

    promedio = (
        sum(v for v in valores if v is not None) / len(valores)
        if valores else 0
    )

    ax_legend.text(
        0.05,
        0.5,
        resultado.nombre,
        fontsize=7.4,
        va="center",
        color="#555555"
    )

    ax_legend.text(
        0.965,
        0.5,
        f"{promedio:.4f}%",
        fontsize=8,
        va="center",
        ha="right",
        color="#222222",
        fontweight="bold"
    )

    # =========================================================
    # EXPORT
    # =========================================================

    buf = io.BytesIO()

    plt.savefig(
        buf,
        format="png",
        dpi=150,
        facecolor="white",
        bbox_inches=None
    )

    plt.close(fig)

    buf.seek(0)

    return buf.getvalue()
