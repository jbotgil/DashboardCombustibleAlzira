"""
Dashboard de Streamlit para visualizar precios de combustible en Alzira.
Diseño moderno con análisis visual mejorado.
"""

import os
from dotenv import load_dotenv
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta, timezone
from database_config import DatabaseConfig

# 1. Cargar las variables del archivo .env
load_dotenv()

# Configuración de la página
st.set_page_config(
    page_title="Precios de Combustible - Alzira",
    page_icon="⛽",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS personalizado para mejor diseño
st.markdown("""
<style>
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 20px;
        border-radius: 15px;
        color: white;
        text-align: center;
    }
    .metric-value {
        font-size: 2.5em;
        font-weight: bold;
    }
    .metric-label {
        font-size: 0.9em;
        opacity: 0.9;
    }
</style>
""", unsafe_allow_html=True)


@st.cache_resource
def get_database():
    """Obtiene la instancia de la base de datos."""
    return DatabaseConfig(
        host=os.getenv("MONGO_HOST", "localhost"),
        port=int(os.getenv("MONGO_PORT", 27017)),
        username=os.getenv("MONGO_USER"),
        password=os.getenv("MONGO_PASS")
    )


@st.cache_data
def get_todos_los_datos(_db):
    """Obtiene todos los datos de la BD."""
    cursor = _db.collection.find().sort("timestamp", -1)
    datos = list(cursor)
    if not datos:
        return pd.DataFrame()
    df = pd.DataFrame(datos)
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    return df


@st.cache_data
def get_ultimo_precio_por_gasolinera(_db):
    """Obtiene el último precio por gasolinera usando agregación."""
    pipeline = [
        {"$sort": {"timestamp": -1}},
        {"$group": {
            "_id": "$nombre",
            "ultimo_precio": {"$first": "$$ROOT"}
        }},
        {"$replaceRoot": {"newRoot": "$ultimo_precio"}}
    ]
    cursor = _db.collection.aggregate(pipeline)
    datos = list(cursor)
    if not datos:
        return pd.DataFrame()
    df = pd.DataFrame(datos)
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    return df


def get_gasolineras(db):
    """Obtiene nombres únicos de gasolineras."""
    return db.get_gasolineras_unicas()


def calcular_estadisticas(df):
    """Calcula estadísticas descriptivas."""
    stats = {}
    for col in ["gasolina_95", "diesel_b7"]:
        if col in df.columns:
            valores = df[col].dropna()
            if len(valores) > 0:
                stats[col] = {
                    "min": valores.min(),
                    "max": valores.max(),
                    "mean": valores.mean(),
                    "median": valores.median(),
                    "std": valores.std()
                }
    return stats


def main():
    # Header con estilo
    st.title("⛽ Dashboard de Precios de Combustible")
    st.markdown("### 📍 Área de Alzira y alrededores")
    st.markdown("---")

    # Conexión a la base de datos
    try:
        db = get_database()
    except Exception as e:
        st.error(f"❌ Error de conexión: {e}")
        return

    # Sidebar
    st.sidebar.header("🔍 Filtros")

    # Selector de combustible
    tipo_comb = st.sidebar.radio(
        "Tipo de combustible",
        ["Ambos", "Gasolina 95 (E5)", "Diésel (B7)"],
        help="Selecciona el tipo de combustible a analizar"
    )

    # Selector de municipio (si hay datos)
    df_completo = get_todos_los_datos(db)

    if not df_completo.empty:
        # Filtrar Alberic (no hay datos relevantes)
        df_completo = df_completo[df_completo["municipio"] != "Alberic"]
        municipios = sorted(df_completo["municipio"].dropna().unique())
        municipio_sel = st.sidebar.selectbox(
            "Municipio",
            ["Todos"] + municipios
        )

        # Selector de rango de precios
        st.sidebar.markdown("### 📊 Rango de precios")
        mostrar_baratos = st.sidebar.checkbox("Mostrar solo los más baratos", value=False)
    else:
        municipio_sel = "Todos"
        mostrar_baratos = False

    if st.sidebar.button("🔄 Actualizar datos", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

    # Carga de datos
    df_ultimos = get_ultimo_precio_por_gasolinera(db)

    if df_ultimos.empty:
        st.warning("⚠️ No hay datos disponibles. Ejecuta el scraper primero.")
        return

    # Filtrar por municipio
    if municipio_sel != "Todos":
        df_ultimos = df_ultimos[df_ultimos["municipio"] == municipio_sel]

    # Filtrar por precio (los más baratos)
    if mostrar_baratos and not df_ultimos.empty:
        if tipo_comb == "Gasolina 95 (E5)":
            df_ultimos = df_ultimos.nsmallest(5, "gasolina_95")
        elif tipo_comb == "Diésel (B7)":
            df_ultimos = df_ultimos.nsmallest(5, "diesel_b7")
        else:
            # Ambos: calcular precio promedio y ordenar
            df_ultimos["precio_promedio"] = (
                df_ultimos["gasolina_95"].fillna(0) +
                df_ultimos["diesel_b7"].fillna(0)
            ) / 2
            df_ultimos = df_ultimos.nsmallest(5, "precio_promedio")

    # Calcular estadísticas
    stats = calcular_estadisticas(df_ultimos)

    # SECCIÓN 1: Métricas principales
    st.header("📊 Resumen Actual")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        if "gasolina_95" in df_ultimos.columns:
            avg_95 = df_ultimos["gasolina_95"].mean()
            min_95 = df_ultimos["gasolina_95"].min()
            max_95 = df_ultimos["gasolina_95"].max()
            st.metric(
                label="⛽ Gasolina 95",
                value=f"{avg_95:.3f} €/L",
                delta=f"Min: {min_95:.3f}€ | Max: {max_95:.3f}€"
            )
        else:
            st.metric("⛽ Gasolina 95", "N/A")

    with col2:
        if "diesel_b7" in df_ultimos.columns:
            avg_b7 = df_ultimos["diesel_b7"].mean()
            min_b7 = df_ultimos["diesel_b7"].min()
            max_b7 = df_ultimos["diesel_b7"].max()
            st.metric(
                label="🚛 Diésel B7",
                value=f"{avg_b7:.3f} €/L",
                delta=f"Min: {min_b7:.3f}€ | Max: {max_b7:.3f}€"
            )
        else:
            st.metric("🚛 Diésel B7", "N/A")

    with col3:
        st.metric(
            label="🏢 Gasolineras",
            value=len(df_ultimos),
            delta=f"en {municipio_sel}"
        )

    with col4:
        # Calcular la más barata
        if not df_ultimos.empty:
            if tipo_comb == "Gasolina 95 (E5)" and "gasolina_95" in df_ultimos.columns:
                mas_barata = df_ultimos.loc[df_ultimos["gasolina_95"].idxmin()]
                st.metric(
                    label="💰 Más barata (95)",
                    value=mas_barata["nombre"][:15] + "..." if len(mas_barata["nombre"]) > 15 else mas_barata["nombre"],
                    delta=f"{mas_barata['gasolina_95']:.3f} €/L"
                )
            elif tipo_comb == "Diésel (B7)" and "diesel_b7" in df_ultimos.columns:
                mas_barata = df_ultimos.loc[df_ultimos["diesel_b7"].idxmin()]
                st.metric(
                    label="💰 Más barata (B7)",
                    value=mas_barata["nombre"][:15] + "..." if len(mas_barata["nombre"]) > 15 else mas_barata["nombre"],
                    delta=f"{mas_barata['diesel_b7']:.3f} €/L"
                )
            else:
                # Ambos combustibles
                df_temp = df_ultimos.copy()
                df_temp["promedio"] = (df_temp["gasolina_95"].fillna(999) + df_temp["diesel_b7"].fillna(999)) / 2
                mas_barata = df_temp.loc[df_temp["promedio"].idxmin()]
                st.metric(
                    label="💰 Más barata",
                    value=mas_barata["nombre"][:15] + "..." if len(mas_barata["nombre"]) > 15 else mas_barata["nombre"],
                    delta="Precio medio"
                )

    st.markdown("---")

    # SECCIÓN 2: Gráfico de barras comparativo
    st.header("📈 Comparativa de Precios por Gasolinera")

    # Preparar datos para gráfico
    df_melt = df_ultimos.melt(
        id_vars=["nombre", "municipio"],
        value_vars=["gasolina_95", "diesel_b7"],
        var_name="Tipo",
        value_name="Precio"
    ).dropna(subset=["Precio"])

    # Mapeo de nombres
    df_melt["Tipo"] = df_melt["Tipo"].map({
        "gasolina_95": "⛽ Gasolina 95",
        "diesel_b7": "🚛 Diésel B7"
    })

    # Crear gráfico de barras
    fig_barras = px.bar(
        df_melt,
        x="nombre",
        y="Precio",
        color="Tipo",
        barmode="group",
        color_discrete_map={
            "⛽ Gasolina 95": "#FF6B6B",
            "🚛 Diésel B7": "#4ECDC4"
        },
        hover_data=["municipio"],
        title="Precios actuales por gasolinera"
    )

    fig_barras.update_layout(
        xaxis_title="Gasolinera",
        yaxis_title="Precio (€/L)",
        plot_bgcolor="rgba(0,0,0,0)",
        hovermode="x unified",
        showlegend=True,
        legend=dict(orientation="h", y=1.1, x=0.5, xanchor="center")
    )

    fig_barras.update_xaxes(tickangle=-45)

    st.plotly_chart(fig_barras, use_container_width=True)

    # SECCIÓN 3: Gráfico de dispersión (Scatter)
    st.header("🎯 Análisis de Relación Precio Gasolina/Diésel")

    df_scatter = df_ultimos.dropna(subset=["gasolina_95", "diesel_b7"]).copy()

    if not df_scatter.empty:
        fig_scatter = px.scatter(
            df_scatter,
            x="gasolina_95",
            y="diesel_b7",
            size=[15] * len(df_scatter),
            hover_name="nombre",
            hover_data=["municipio"],
            title="Relación entre precios de Gasolina 95 y Diésel B7",
            labels={
                "gasolina_95": "Precio Gasolina 95 (€/L)",
                "diesel_b7": "Precio Diésel B7 (€/L)"
            },
            color="diesel_b7",
            color_continuous_scale="RdYlGn_r"  # Rojo (caro) a Verde (barato)
        )

        # Añadir línea de tendencia
        fig_scatter.add_trace(
            go.Scatter(
                x=df_scatter["gasolina_95"],
                y=df_scatter["diesel_b7"],
                mode="markers",
                marker=dict(size=12, line=dict(width=2, color="DarkSlateGrey")),
                showlegend=False
            )
        )

        fig_scatter.update_layout(
            plot_bgcolor="rgba(240,240,240,0.5)",
            hovermode="closest"
        )

        st.plotly_chart(fig_scatter, use_container_width=True)
    else:
        st.info("No hay datos completos para mostrar el análisis de relación.")

    # SECCIÓN 4: Mapa de calor (Heatmap)
    st.header("🔥 Mapa de Calor de Precios")

    # Crear matriz para heatmap
    df_heatmap = df_ultimos.set_index("nombre")[["gasolina_95", "diesel_b7"]].copy()
    df_heatmap.columns = ["⛽ Gasolina 95", "🚛 Diésel B7"]

    if not df_heatmap.empty:
        fig_heatmap = go.Figure(data=go.Heatmap(
            z=df_heatmap.values,
            x=df_heatmap.columns,
            y=df_heatmap.index,
            colorscale="RdYlGn_r",
            hovertemplate="%{y}<br>%{x}: %{z:.3f}€/L<extra></extra>",
            showscale=True
        ))

        fig_heatmap.update_layout(
            title="Mapa de calor de precios por gasolinera",
            xaxis_title="Tipo de combustible",
            yaxis_title="Gasolinera",
            height=max(300, len(df_heatmap) * 40)
        )

        st.plotly_chart(fig_heatmap, use_container_width=True)

    # SECCIÓN 5: Tabla de datos ordenada
    st.header("📋 Ranking de Precios")

    col_tab1, col_tab2 = st.tabs(["⛽ Gasolina 95", "🚛 Diésel B7"])

    with col_tab1:
        if "gasolina_95" in df_ultimos.columns:
            df_ranking_95 = df_ultimos[["nombre", "municipio", "gasolina_95"]].dropna(
                subset=["gasolina_95"]
            ).sort_values("gasolina_95").reset_index(drop=True)
            df_ranking_95.index = df_ranking_95.index + 1
            df_ranking_95 = df_ranking_95.rename(
                columns={"nombre": "Gasolinera", "municipio": "Municipio", "gasolina_95": "Precio (€/L)"}
            )
            st.dataframe(
                df_ranking_95.style.format({"Precio (€/L)": "{:.3f} €"})
                .background_gradient(subset=["Precio (€/L)"], cmap="RdYlGn_r"),
                use_container_width=True,
                hide_index=True
            )
        else:
            st.info("No hay datos de gasolina 95.")

    with col_tab2:
        if "diesel_b7" in df_ultimos.columns:
            df_ranking_b7 = df_ultimos[["nombre", "municipio", "diesel_b7"]].dropna(
                subset=["diesel_b7"]
            ).sort_values("diesel_b7").reset_index(drop=True)
            df_ranking_b7.index = df_ranking_b7.index + 1
            df_ranking_b7 = df_ranking_b7.rename(
                columns={"nombre": "Gasolinera", "municipio": "Municipio", "diesel_b7": "Precio (€/L)"}
            )
            st.dataframe(
                df_ranking_b7.style.format({"Precio (€/L)": "{:.3f} €"})
                .background_gradient(subset=["Precio (€/L)"], cmap="RdYlGn_r"),
                use_container_width=True,
                hide_index=True
            )
        else:
            st.info("No hay datos de diésel B7.")

    # SECCIÓN 6: Estadísticas descriptivas
    with st.expander("📊 Ver estadísticas descriptivas"):
        col_stat1, col_stat2 = st.columns(2)

        with col_stat1:
            if "gasolina_95" in stats:
                st.subheader("⛽ Gasolina 95")
                st.write(f"- **Mínimo:** {stats['gasolina_95']['min']:.3f} €/L")
                st.write(f"- **Máximo:** {stats['gasolina_95']['max']:.3f} €/L")
                st.write(f"- **Media:** {stats['gasolina_95']['mean']:.3f} €/L")
                st.write(f"- **Mediana:** {stats['gasolina_95']['median']:.3f} €/L")
                st.write(f"- **Desviación:** {stats['gasolina_95']['std']:.3f} €/L")

        with col_stat2:
            if "diesel_b7" in stats:
                st.subheader("🚛 Diésel B7")
                st.write(f"- **Mínimo:** {stats['diesel_b7']['min']:.3f} €/L")
                st.write(f"- **Máximo:** {stats['diesel_b7']['max']:.3f} €/L")
                st.write(f"- **Media:** {stats['diesel_b7']['mean']:.3f} €/L")
                st.write(f"- **Mediana:** {stats['diesel_b7']['median']:.3f} €/L")
                st.write(f"- **Desviación:** {stats['diesel_b7']['std']:.3f} €/L")

    # Footer
    st.markdown("---")
    st.caption(
        f"Datos actualizados: {datetime.now().strftime('%d/%m/%Y %H:%M')} | "
        f"Fuente: Ministerio de Industria y Turismo"
    )


if __name__ == "__main__":
    main()
