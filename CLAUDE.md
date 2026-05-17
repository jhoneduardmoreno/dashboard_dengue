# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Dengue Early Warning System (SAT Dengue) — Streamlit dashboard + FastAPI service for predicting dengue epidemic excess in **3 focus municipalities** (Entrega 3). Academic project for MAIA (Universidad de los Andes).

Focus municipalities (D1):

- `23855` Valencia (Córdoba, Caribe)
- `47288` Fundación (Magdalena, Sierra Nevada)
- `95025` El Retorno (Guaviare, Amazonía)

Full methodology and design decisions are in `docs/decisiones_proyecto.md` (D1–D17). When in doubt about target definition, feature engineering, model choice, tuning or evaluation, consult that file first.

## Environment

The project uses a dedicated conda environment named `dashboard_dengue`. Always activate it before running any command:

```bash
conda activate dashboard_dengue
pip install -r requirements.txt   # if dependencies changed
```

## Commands

```bash
streamlit run app.py        # dashboard at http://localhost:8501
uvicorn api:app --reload    # API at http://localhost:8000 (docs at /docs)
```

## Architecture

Three core artifacts plus shared metadata:

- **`foco_models.joblib`** — Per-municipio bundle. Structure:
  ```
  { cod_mpio (str): {
      "municipio": str,
      "logistic": {"model": LogisticRegression, "scaler": StandardScaler, "features": list[str]},
      "xgboost":  {"model": XGBClassifier,     "scaler": StandardScaler, "features": list[str], "best_params": dict}
  } }
  ```
  28 features per model (D15): clima actual + lags 1-3 + medias móviles 3m + casos/incidencia lags + `mes_sin`/`mes_cos`.

- **`panel_municipal_mensual.csv`** — Mensual 2007-2024 × 3 municipios (648 rows × 42 cols). Key cols: `cod_mpio`, `municipio`, `ano`, `mes`, `casos_total`, `incidencia_x100k`, `temperatura_c`, `precipitacion_mm`, `ndvi`, `dewpoint_c`, todos los lags/medias móviles, `umbral_exceso`, `exceso`. **No** contiene `mes_sin`/`mes_cos` — `app.py` los computa al cargar.

- **`predicciones_test.csv`** — Predicciones cacheadas 2020-2024 × 3 municipios × 3 modelos (baseline/logistic/xgboost). Columnas: `cod_mpio`, `ano`, `mes`, `casos_total`, `exceso`, `pred_baseline`, `pred_logistic`, `proba_logistic`, `pred_xgboost`, `proba_xgboost`. Única fuente de métricas en el dashboard.

- **`foco_meta.py`** — Constantes compartidas: `FOCO_META` (nombre, depto, región, lat/lon), `THRESHOLDS = {"riesgo": 0.3, "alerta": 0.6}`, `MODEL_TYPES = ["logistic", "xgboost"]`. Reusar siempre estas constantes en lugar de duplicarlas.

### App Structure (`app.py`)

Single-file Streamlit app. Secciones top-to-bottom:

1. **Config, estilos, constantes** — `MODEL_LABELS`, `DASHBOARD_MODELS = ["xgboost","logistic","baseline"]`, `LEVEL_COLORS`, `MESES_NOMBRES`.
2. **Loaders cacheados** — `load_bundle()`, `load_panel()`, `load_test_predictions()`, `compute_metrics()`.
3. **`predict_municipio(df_panel, bundle, cod_mpio, model_type)`** — Aplica el modelo del municipio (o regla baseline D17) y devuelve copia con `probabilidad_exceso`, `pred`, `nivel_alerta`.
4. **Sidebar** — selector municipio foco, radio modelo, año, mes; tarjeta de metadata.
5. **Fila 1** — Mapa scattergeo (3 puntos foco con color por nivel) + serie temporal 2007-2024 con marcadores de exceso real/predicho.
6. **Fila 2** — Curva de probabilidad en test + panel de riesgo con métricas (Precision/Recall/F1/Accuracy).
7. **Descarga CSV** del municipio activo.
8. **Expander metodología** con features, hiperparámetros, métricas y referencia a `docs/decisiones_proyecto.md`.

### API Structure (`api.py`)

FastAPI con `lifespan` que carga `foco_models.joblib` y valida contra `FOCO_META`.

Endpoints:
- `GET /health` — bundle status + thresholds.
- `GET /municipios` — los 3 focos con coords y región.
- `GET /features?cod_mpio=...&model_type=...` — features del modelo solicitado.
- `POST /predict` — body `PredictRequest{cod_mpio, model_type, features}`. Valida que `cod_mpio` exista (404), `model_type` válido (400), no falten features (422). Aplica `scaler.transform` + `predict_proba` y devuelve probabilidad + nivel.

## Convenciones

- **Idioma:** UI, nombres de variables y comentarios en **español**. Mantener.
- **Thresholds:** SIEMPRE leer de `foco_meta.THRESHOLDS`. No hardcodear 0.3/0.6.
- **Niveles:** `Normal` < `THRESHOLDS["riesgo"]`, `Riesgo` ∈ [riesgo, alerta), `Alerta` ≥ `THRESHOLDS["alerta"]`.
- **`cod_mpio`:** siempre `str` en el dashboard y la API (keys del bundle son `str`).
- **`mes_sin`/`mes_cos`:** computados en `load_panel()` con `sin/cos(2π·mes/12)`.
- **Cortes temporales:** train 2007-2019, test 2020-2024. `predicciones_test.csv` cubre solo test.

## Add-only

No introducir nuevas dependencias sin actualizar `requirements.txt`. No agregar municipios fuera de los 3 focos sin re-entrenar el bundle.
