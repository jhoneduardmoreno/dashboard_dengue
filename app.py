"""
Sistema de Alerta Temprana de Dengue - 3 municipios foco
Dashboard interactivo
MAIA — Universidad de los Andes

Metodología y decisiones: docs/decisiones_proyecto.md (D1-D17).
"""

import io

import joblib
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score

from foco_meta import FOCO_META, MODEL_TYPES, THRESHOLDS

# ============================================================
# CONFIGURACIÓN DE LA PÁGINA
# ============================================================
st.set_page_config(
    page_title="SAT Dengue — 3 Focos",
    page_icon="🦟",
    layout="wide",
    initial_sidebar_state="expanded",
)

MODEL_LABELS = {
    "xgboost": "XGBoost",
    "logistic": "Regresión Logística",
    "baseline": "Baseline trivial",
}
DASHBOARD_MODELS = ["xgboost", "logistic", "baseline"]
LEVEL_COLORS = {"Normal": "#22c55e", "Riesgo": "#eab308", "Alerta": "#ef4444"}

MESES_NOMBRES = {
    1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril",
    5: "Mayo", 6: "Junio", 7: "Julio", 8: "Agosto",
    9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre",
}

# ============================================================
# ESTILOS
# ============================================================
st.markdown(
    """
<style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;700&family=Space+Mono:wght@400;700&display=swap');
    .stApp { font-family: 'DM Sans', sans-serif; }
    .main-header {
        background: linear-gradient(135deg, #1b2838 0%, #1a3a5c 50%, #1a5276 100%);
        padding: 1.5rem 2rem; border-radius: 12px; margin-bottom: 1.5rem;
        border-bottom: 4px solid #e74c3c;
    }
    .main-header h1 { color:#fff; font-family:'Space Mono',monospace; font-size:1.6rem; margin:0; }
    .main-header p  { color:#a8b2d1; font-size:0.9rem; margin:0.3rem 0 0 0; }
    .risk-alta { background: linear-gradient(135deg,#fee2e2,#fecaca); border:2px solid #dc2626; }
    .risk-moderada { background: linear-gradient(135deg,#fef9c3,#fef08a); border:2px solid #ca8a04; }
    .risk-normal { background: linear-gradient(135deg,#dcfce7,#bbf7d0); border:2px solid #16a34a; }
    .risk-nd { background: linear-gradient(135deg,#f1f5f9,#e2e8f0); border:2px solid #94a3b8; }
    .variable-row { display:flex; align-items:center; padding:0.5rem 0; border-bottom:1px solid rgba(0,0,0,0.08); font-size:0.95rem; }
    .variable-row:last-child { border-bottom:none; }
    .variable-icon { font-size:1.2rem; margin-right:0.5rem; width:28px; text-align:center; }
    .variable-label { color:#475569; flex:1; }
    .variable-value { font-family:'Space Mono',monospace; font-weight:700; color:#1e293b; }
    .section-title {
        font-family:'Space Mono',monospace; font-size:1rem; font-weight:700;
        color:#1e293b; margin-bottom:0.8rem; padding-bottom:0.4rem; border-bottom:2px solid #e5e7eb;
    }
    .metric-card { background:#fff; border-radius:10px; padding:0.8rem 1rem; box-shadow:0 1px 6px rgba(0,0,0,0.06); text-align:center; }
    .metric-card .label { font-size:0.75rem; color:#64748b; text-transform:uppercase; letter-spacing:0.05em; }
    .metric-card .value { font-family:'Space Mono',monospace; font-size:1.3rem; font-weight:700; color:#1e293b; }
</style>
""",
    unsafe_allow_html=True,
)

# ============================================================
# CARGA DE DATOS, BUNDLE Y PREDICCIONES DE TEST
# ============================================================
@st.cache_resource
def load_bundle():
    bundle = joblib.load("foco_models.joblib")
    return bundle


@st.cache_data
def load_panel():
    df = pd.read_csv("panel_municipal_mensual.csv")
    df["cod_mpio"] = df["cod_mpio"].astype(str)
    df["fecha"] = pd.to_datetime(
        df["ano"].astype(str) + "-" + df["mes"].astype(str).str.zfill(2) + "-01"
    )
    # Features cíclicas estacionales (D15) — no se almacenan en el panel
    df["mes_sin"] = np.sin(2 * np.pi * df["mes"] / 12)
    df["mes_cos"] = np.cos(2 * np.pi * df["mes"] / 12)
    return df


@st.cache_data
def load_test_predictions():
    tp = pd.read_csv("predicciones_test.csv")
    tp["cod_mpio"] = tp["cod_mpio"].astype(str)
    tp["fecha"] = pd.to_datetime(
        tp["ano"].astype(str) + "-" + tp["mes"].astype(str).str.zfill(2) + "-01"
    )
    return tp


@st.cache_data
def compute_metrics(_test_df: pd.DataFrame) -> dict:
    """Calcula Precision/Recall/F1/Accuracy por (cod_mpio, modelo) desde test set."""
    out: dict = {}
    for cod, g in _test_df.groupby("cod_mpio"):
        out[cod] = {}
        for m in DASHBOARD_MODELS:
            y_true = g["exceso"].astype(int)
            y_pred = g[f"pred_{m}"].astype(int)
            out[cod][m] = {
                "precision": precision_score(y_true, y_pred, zero_division=0),
                "recall": recall_score(y_true, y_pred, zero_division=0),
                "f1": f1_score(y_true, y_pred, zero_division=0),
                "accuracy": accuracy_score(y_true, y_pred),
                "n": int(len(g)),
                "positivos": int(y_true.sum()),
            }
    return out


def predict_municipio(df_panel: pd.DataFrame, bundle: dict, cod_mpio: str, model_type: str) -> pd.DataFrame:
    """Aplica el modelo del municipio al panel completo. Devuelve copia con
    columnas `probabilidad_exceso`, `pred` y `nivel_alerta`."""
    sub = df_panel[df_panel["cod_mpio"] == cod_mpio].copy()
    sub["probabilidad_exceso"] = np.nan
    sub["pred"] = np.nan

    if model_type == "baseline":
        sub["pred"] = (sub["casos_total_lag1"] > 2).astype("Int64")
        # Sin probabilidad real: usamos pred como proxy para alertar
        sub["probabilidad_exceso"] = sub["pred"].astype(float)
    else:
        artefactos = bundle[cod_mpio][model_type]
        feats = artefactos["features"]
        scaler = artefactos["scaler"]
        model = artefactos["model"]
        mask = sub[feats].notna().all(axis=1)
        if mask.any():
            X = sub.loc[mask, feats].values
            X_scaled = scaler.transform(X)
            probas = model.predict_proba(X_scaled)[:, 1]
            sub.loc[mask, "probabilidad_exceso"] = probas
            sub.loc[mask, "pred"] = (probas >= THRESHOLDS["alerta"]).astype(int)

    sub["nivel_alerta"] = pd.cut(
        sub["probabilidad_exceso"],
        bins=[-0.01, THRESHOLDS["riesgo"], THRESHOLDS["alerta"], 1.01],
        labels=["Normal", "Riesgo", "Alerta"],
    )
    return sub


# ============================================================
# CARGA INICIAL
# ============================================================
try:
    bundle = load_bundle()
    df_panel = load_panel()
    test_preds = load_test_predictions()
    metrics_by_mpio = compute_metrics(test_preds)
    bundle_ok = set(bundle.keys()) == set(FOCO_META.keys())
    if not bundle_ok:
        st.warning(
            f"Inconsistencia: bundle={set(bundle.keys())} vs FOCO_META={set(FOCO_META.keys())}"
        )
    data_loaded = True
except Exception as e:  # noqa: BLE001
    data_loaded = False
    st.error(f"Error cargando datos o modelos: {e}")

if not data_loaded:
    st.stop()

# ============================================================
# HEADER
# ============================================================
st.markdown(
    """
<div class="main-header">
    <h1>🦟 Sistema de Alerta Temprana de Dengue</h1>
    <p>Predicción de exceso epidémico — 3 municipios foco · Modelos per-municipio (Logística + XGBoost)</p>
</div>
""",
    unsafe_allow_html=True,
)

# ============================================================
# SIDEBAR
# ============================================================
with st.sidebar:
    st.markdown("### ⚙️ Filtros")
    st.markdown("---")

    cod_mpio = st.selectbox(
        "🏘️ Municipio foco",
        list(FOCO_META.keys()),
        format_func=lambda c: f"{FOCO_META[c]['municipio']} — {FOCO_META[c]['depto']}",
    )

    model_type = st.radio(
        "🧠 Modelo",
        DASHBOARD_MODELS,
        format_func=lambda m: MODEL_LABELS[m],
        index=0,
        help="XGBoost es el modelo por defecto (D5). Baseline trivial (D17): pred=1 si casos_lag1>2.",
    )

    st.markdown("---")

    df_mpio = df_panel[df_panel["cod_mpio"] == cod_mpio]
    anos_disp = sorted(df_mpio["ano"].unique(), reverse=True)
    ano_sel = st.selectbox("📅 Año", anos_disp, index=0)

    meses_disp = sorted(df_mpio[df_mpio["ano"] == ano_sel]["mes"].unique())
    mes_sel = st.selectbox(
        "🗓️ Mes",
        meses_disp,
        format_func=lambda x: MESES_NOMBRES.get(x, str(x)),
        index=len(meses_disp) - 1,
    )

    st.markdown("---")
    meta = FOCO_META[cod_mpio]
    st.markdown(
        f"""
        <div style='font-size:0.85rem; color:#475569; line-height:1.5;'>
            <b>{meta['municipio']}</b><br>
            Depto: {meta['depto']}<br>
            Región: {meta['region']}<br>
            Modelo activo: <b>{MODEL_LABELS[model_type]}</b>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("---")
    st.markdown(
        """
        <div style='text-align:center; color:#94a3b8; font-size:0.75rem;'>
            MAIA — Universidad de los Andes<br>
            2026
        </div>
        """,
        unsafe_allow_html=True,
    )

# ============================================================
# PREDICCIONES PARA EL MUNICIPIO + MODELO ACTIVOS
# ============================================================
df_pred = predict_municipio(df_panel, bundle, cod_mpio, model_type)
df_periodo = df_pred[(df_pred["ano"] == ano_sel) & (df_pred["mes"] == mes_sel)]
periodo_label = f"{MESES_NOMBRES[mes_sel]} {ano_sel}"

# Para mapa: nivel del periodo de cada municipio foco (usando modelo activo)
df_map_rows = []
for cod, m in FOCO_META.items():
    sub = predict_municipio(df_panel, bundle, cod, model_type)
    fila = sub[(sub["ano"] == ano_sel) & (sub["mes"] == mes_sel)]
    if len(fila):
        r = fila.iloc[0]
        df_map_rows.append(
            {
                "cod_mpio": cod,
                "municipio": m["municipio"],
                "depto": m["depto"],
                "lat": m["lat"],
                "lon": m["lon"],
                "prob": r["probabilidad_exceso"],
                "nivel": r["nivel_alerta"],
                "casos": int(r["casos_total"]) if pd.notna(r["casos_total"]) else 0,
            }
        )
df_map = pd.DataFrame(df_map_rows)

# ============================================================
# FILA 1: MAPA + SERIE TEMPORAL
# ============================================================
col_map, col_ts = st.columns([1, 1])

with col_map:
    st.markdown('<div class="section-title">🗺️ Mapa de alerta — Municipios foco</div>', unsafe_allow_html=True)

    fig_map = go.Figure()
    for nivel, color in LEVEL_COLORS.items():
        d_n = df_map[df_map["nivel"].astype(str) == nivel]
        if len(d_n) > 0:
            fig_map.add_trace(
                go.Scattergeo(
                    lat=d_n["lat"], lon=d_n["lon"],
                    text=d_n.apply(
                        lambda r: (
                            f"<b>{r['municipio']}</b> ({r['depto']})<br>"
                            f"Prob. exceso: {r['prob']*100:.1f}%<br>"
                            f"Casos: {r['casos']}"
                            if pd.notna(r["prob"]) else
                            f"<b>{r['municipio']}</b> ({r['depto']})<br>Sin datos suficientes"
                        ),
                        axis=1,
                    ),
                    hoverinfo="text",
                    marker=dict(size=20, color=color, opacity=0.85,
                                line=dict(width=2, color="white")),
                    name=nivel,
                )
            )
    # Municipios sin nivel (NaN)
    d_nan = df_map[df_map["nivel"].isna()]
    if len(d_nan) > 0:
        fig_map.add_trace(
            go.Scattergeo(
                lat=d_nan["lat"], lon=d_nan["lon"],
                text=d_nan.apply(
                    lambda r: f"<b>{r['municipio']}</b> ({r['depto']})<br>Sin datos suficientes",
                    axis=1,
                ),
                hoverinfo="text",
                marker=dict(size=18, color="#94a3b8", opacity=0.7,
                            line=dict(width=2, color="white")),
                name="N/D",
            )
        )

    fig_map.update_geos(
        scope="south america", center=dict(lat=5.5, lon=-73.5),
        projection_scale=4.0,
        showland=True, landcolor="#f1f5f9",
        showocean=True, oceancolor="#e0f2fe",
        showcountries=True, countrycolor="#94a3b8",
        showframe=False, bgcolor="rgba(0,0,0,0)",
    )
    fig_map.update_layout(
        height=480, margin=dict(t=10, b=10, l=0, r=0),
        paper_bgcolor="rgba(0,0,0,0)",
        legend=dict(orientation="h", yanchor="bottom", y=-0.05, xanchor="center", x=0.5, font=dict(size=11)),
        font_family="DM Sans",
    )
    st.plotly_chart(fig_map, use_container_width=True)

with col_ts:
    st.markdown('<div class="section-title">📈 Casos reales 2007-2024 + predicciones test 2020-2024</div>', unsafe_allow_html=True)

    df_ts = df_pred.sort_values("fecha")
    tp_mpio = test_preds[test_preds["cod_mpio"] == cod_mpio].sort_values("fecha")

    fig_ts = go.Figure()
    fig_ts.add_trace(
        go.Scatter(
            x=df_ts["fecha"], y=df_ts["casos_total"],
            name="Casos reales",
            line=dict(color="#3b82f6", width=2),
            mode="lines",
            fill="tozeroy",
            fillcolor="rgba(59,130,246,0.10)",
        )
    )
    # Marcadores: exceso real (verdad) y exceso predicho por el modelo activo
    real_excess = tp_mpio[tp_mpio["exceso"] == 1]
    pred_col = f"pred_{model_type}"
    pred_excess = tp_mpio[tp_mpio[pred_col] == 1]

    fig_ts.add_trace(
        go.Scatter(
            x=real_excess["fecha"], y=real_excess["casos_total"],
            mode="markers", name="Exceso real (test)",
            marker=dict(symbol="circle", size=11, color="#1e293b",
                        line=dict(width=2, color="white")),
        )
    )
    fig_ts.add_trace(
        go.Scatter(
            x=pred_excess["fecha"], y=pred_excess["casos_total"],
            mode="markers", name=f"Exceso predicho ({MODEL_LABELS[model_type]})",
            marker=dict(symbol="x", size=12, color="#ef4444", line=dict(width=2)),
        )
    )

    fig_ts.add_shape(
        type="line", x0="2020-01-01", x1="2020-01-01", xref="x",
        y0=0, y1=1, yref="paper",
        line=dict(color="#94a3b8", width=1, dash="dash"),
    )
    fig_ts.add_annotation(
        x="2020-01-01", y=1.0, xref="x", yref="paper",
        text="Inicio test", showarrow=False, yshift=10, font=dict(size=10),
    )

    fig_ts.update_layout(
        height=450, font_family="DM Sans",
        plot_bgcolor="#fafafa", paper_bgcolor="rgba(0,0,0,0)",
        margin=dict(t=30, b=40, l=50, r=20), yaxis_title="Casos",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5),
        hovermode="x unified",
    )
    fig_ts.update_xaxes(gridcolor="#e5e7eb")
    fig_ts.update_yaxes(gridcolor="#e5e7eb")
    st.plotly_chart(fig_ts, use_container_width=True)

# ============================================================
# FILA 2: PROBABILIDAD (test) + PANEL DE RIESGO
# ============================================================
col_prob, col_risk = st.columns([1, 1])

with col_prob:
    st.markdown('<div class="section-title">⚠️ Probabilidad de exceso — test 2020-2024</div>', unsafe_allow_html=True)

    tp_mpio = test_preds[test_preds["cod_mpio"] == cod_mpio].sort_values("fecha")
    proba_col = f"proba_{model_type}" if model_type != "baseline" else None

    if proba_col is None:
        st.info("El baseline trivial (D17) no produce probabilidades, solo predicciones 0/1.")
    elif tp_mpio.empty:
        st.info("No hay predicciones de test disponibles para este municipio.")
    else:
        fig_p = go.Figure()
        fig_p.add_hrect(y0=0, y1=THRESHOLDS["riesgo"], fillcolor="rgba(34,197,94,0.1)", line_width=0)
        fig_p.add_hrect(y0=THRESHOLDS["riesgo"], y1=THRESHOLDS["alerta"],
                        fillcolor="rgba(234,179,8,0.1)", line_width=0)
        fig_p.add_hrect(y0=THRESHOLDS["alerta"], y1=1.0,
                        fillcolor="rgba(239,68,68,0.1)", line_width=0)
        fig_p.add_trace(
            go.Scatter(
                x=tp_mpio["fecha"], y=tp_mpio[proba_col],
                name=f"Prob. ({MODEL_LABELS[model_type]})",
                mode="lines+markers",
                line=dict(color="#1e293b", width=2.2),
                marker=dict(size=6),
            )
        )
        fig_p.add_hline(
            y=THRESHOLDS["riesgo"], line_dash="dash", line_color="#22c55e", line_width=1,
            annotation_text=f"Riesgo ({THRESHOLDS['riesgo']})",
            annotation_position="right", annotation_font_color="#22c55e", annotation_font_size=10,
        )
        fig_p.add_hline(
            y=THRESHOLDS["alerta"], line_dash="dash", line_color="#ef4444", line_width=1,
            annotation_text=f"Alerta ({THRESHOLDS['alerta']})",
            annotation_position="right", annotation_font_color="#ef4444", annotation_font_size=10,
        )
        fig_p.update_layout(
            height=380, font_family="DM Sans",
            plot_bgcolor="#fafafa", paper_bgcolor="rgba(0,0,0,0)",
            margin=dict(t=20, b=40, l=50, r=70),
            yaxis=dict(title="Probabilidad", range=[0, 1.02], gridcolor="#e5e7eb"),
            xaxis=dict(gridcolor="#e5e7eb"),
            showlegend=False, hovermode="x unified",
        )
        st.plotly_chart(fig_p, use_container_width=True)

with col_risk:
    st.markdown('<div class="section-title">🎯 Panel de riesgo — periodo seleccionado</div>', unsafe_allow_html=True)

    if df_periodo.empty:
        st.info("No hay datos para el período seleccionado.")
    else:
        row = df_periodo.iloc[0]
        prob = row["probabilidad_exceso"]
        nivel = row["nivel_alerta"]

        if pd.isna(prob):
            nivel_text, panel_class, emoji, color = "SIN DATOS", "risk-nd", "⚪", "#94a3b8"
            prob_view = 0.0
        elif nivel == "Alerta":
            nivel_text, panel_class, emoji, color = "ALTO", "risk-alta", "🔴", "#dc2626"
            prob_view = float(prob)
        elif nivel == "Riesgo":
            nivel_text, panel_class, emoji, color = "MODERADO", "risk-moderada", "🟡", "#ca8a04"
            prob_view = float(prob)
        else:
            nivel_text, panel_class, emoji, color = "NORMAL", "risk-normal", "🟢", "#16a34a"
            prob_view = float(prob)

        es_test = 2020 <= ano_sel <= 2024
        leyenda_periodo = "periodo de test" if es_test else "fuera de test — sin métrica oficial"

        st.markdown(
            f"""
        <div class="{panel_class}" style="margin-bottom: 1rem; border-radius: 12px; padding: 1.2rem;">
            <div style="display:flex; align-items:center; margin-bottom:0.4rem;">
                <span style="font-size:1.4rem; margin-right:0.5rem;">⚠️</span>
                <span style="font-family:'Space Mono',monospace; font-weight:700; font-size:1rem;">
                    Probabilidad de exceso: <span style="color:{color};">{prob_view*100:.1f}%</span>
                </span>
            </div>
            <div style="font-size:1.2rem; font-weight:700; margin-bottom:0.3rem;">
                Nivel: {emoji} {nivel_text}
            </div>
            <div style="font-size:0.78rem; color:#475569;">
                {FOCO_META[cod_mpio]['municipio']} ({FOCO_META[cod_mpio]['depto']}) — {periodo_label} · {leyenda_periodo}
            </div>
        </div>
        """,
            unsafe_allow_html=True,
        )

        m = metrics_by_mpio.get(cod_mpio, {}).get(model_type)
        if m is not None:
            c1, c2, c3, c4 = st.columns(4)
            for c, label, val in (
                (c1, "Precision", m["precision"]),
                (c2, "Recall", m["recall"]),
                (c3, "F1", m["f1"]),
                (c4, "Accuracy", m["accuracy"]),
            ):
                with c:
                    st.markdown(
                        f'<div class="metric-card"><div class="label">{label}</div>'
                        f'<div class="value">{val:.2f}</div></div>',
                        unsafe_allow_html=True,
                    )
            st.caption(
                f"Métricas en test 2020-2024 (n={m['n']}, positivos={m['positivos']}) · "
                f"modelo {MODEL_LABELS[model_type]}"
            )

        casos_total = int(row["casos_total"]) if pd.notna(row["casos_total"]) else 0
        st.markdown(
            f"""
        <div style="background:#fff; border-radius:12px; padding:1rem 1.2rem; margin-top:0.8rem;
                    box-shadow:0 2px 12px rgba(0,0,0,0.06);">
            <div style="font-weight:700; font-size:0.9rem; margin-bottom:0.6rem; color:#1e293b;">
                Variables del periodo
            </div>
            <div class="variable-row">
                <span class="variable-icon">🌧️</span><span class="variable-label">Lluvia</span>
                <span class="variable-value">{row['precipitacion_mm']:.0f} mm</span>
            </div>
            <div class="variable-row">
                <span class="variable-icon">🌡️</span><span class="variable-label">Temperatura</span>
                <span class="variable-value">{row['temperatura_c']:.1f}°C</span>
            </div>
            <div class="variable-row">
                <span class="variable-icon">🌿</span><span class="variable-label">NDVI</span>
                <span class="variable-value">{row['ndvi']:.3f}</span>
            </div>
            <div class="variable-row">
                <span class="variable-icon">👥</span><span class="variable-label">Población</span>
                <span class="variable-value">{row['poblacion']:,.0f}</span>
            </div>
            <div class="variable-row">
                <span class="variable-icon">🏥</span><span class="variable-label">Casos en el mes</span>
                <span class="variable-value">{casos_total:,}</span>
            </div>
        </div>
        """,
            unsafe_allow_html=True,
        )

st.markdown("<br>", unsafe_allow_html=True)

# ============================================================
# DESCARGAR REPORTE
# ============================================================
st.markdown("---")
col_dl1, col_dl2, col_dl3 = st.columns([2, 1, 2])
with col_dl2:
    df_export = df_pred[
        [
            "cod_mpio", "municipio", "ano", "mes", "casos_total",
            "incidencia_x100k", "temperatura_c", "precipitacion_mm", "ndvi",
            "probabilidad_exceso", "nivel_alerta", "exceso",
        ]
    ].copy()
    csv_buffer = io.StringIO()
    df_export.to_csv(csv_buffer, index=False)
    st.download_button(
        label=f"📥 Descargar serie {FOCO_META[cod_mpio]['municipio']}",
        data=csv_buffer.getvalue(),
        file_name=f"sat_dengue_{cod_mpio}_{model_type}.csv",
        mime="text/csv",
        use_container_width=True,
    )

# ============================================================
# INFO DEL MODELO
# ============================================================
with st.expander("ℹ️ Acerca del modelo y la metodología"):
    if model_type == "baseline":
        feats_info = "Baseline trivial (D17): predicción = 1 si `casos_total_lag1` > 2."
        params_info = "Sin hiperparámetros."
    else:
        art = bundle[cod_mpio][model_type]
        feats_info = ", ".join(art["features"])
        if model_type == "xgboost":
            params_info = f"Hiperparámetros tuneados (D16): {art.get('best_params')}"
        else:
            params_info = "Logística L2 con `class_weight='balanced'` (D5/D16)."

    m_all = metrics_by_mpio.get(cod_mpio, {})
    tabla_metricas = "\n".join(
        f"- **{MODEL_LABELS[k]}** — Precision: {v['precision']:.2f} · "
        f"Recall: {v['recall']:.2f} · F1: {v['f1']:.2f} · Acc: {v['accuracy']:.2f}"
        for k, v in m_all.items()
    )

    st.markdown(
        f"""
**Municipio:** {FOCO_META[cod_mpio]['municipio']} ({FOCO_META[cod_mpio]['depto']}, {FOCO_META[cod_mpio]['region']}) · cod_mpio `{cod_mpio}`
**Modelo activo:** {MODEL_LABELS[model_type]}

**Features ({len(bundle[cod_mpio]['logistic']['features']) if model_type != 'baseline' else 1}):** {feats_info}

**Hiperparámetros:** {params_info}

**Métricas test 2020-2024 para este municipio:**
{tabla_metricas}

**Target (D12):** `exceso = 1` si `casos_total > umbral`, donde `umbral = max(P75 histórico por mes calendario, 2)`.

**Thresholds (D5):** Normal `< {THRESHOLDS['riesgo']}` · Riesgo `[{THRESHOLDS['riesgo']}, {THRESHOLDS['alerta']})` · Alerta `≥ {THRESHOLDS['alerta']}`.

Metodología completa: `docs/decisiones_proyecto.md` (D1–D17).
"""
    )

# ============================================================
# FOOTER
# ============================================================
st.markdown(
    """
<div style="text-align:center; color:#94a3b8; font-size:0.75rem; margin-top:2rem; padding:1rem;">
    Sistema de Alerta Temprana de Dengue<br>
    MAIA — Universidad de los Andes — 2026<br>
    Danilo Camargo · Jhon Eduard Moreno Díaz · Hernán Javier Silva Sosa · Sheyla Ruby Zela Quirita
</div>
""",
    unsafe_allow_html=True,
)
