# 🦟 Sistema de Alerta Temprana de Dengue — 3 Municipios Foco

Dashboard interactivo (Streamlit) y API REST (FastAPI) para predecir exceso epidémico de dengue en tres municipios foco del microproyecto MAIA — Universidad de los Andes.

## Alcance (Entrega 3)

Modelos independientes por municipio (D1, D5):

| Código | Municipio | Departamento | Región |
|--------|-----------|--------------|--------|
| 23855  | Valencia  | Córdoba      | Caribe |
| 47288  | Fundación | Magdalena    | Sierra Nevada |
| 95025  | El Retorno| Guaviare     | Amazonía |

Cada municipio tiene un par de modelos (`logistic`, `xgboost`) entrenados sobre 2007–2019 y evaluados en 2020–2024. El baseline trivial (D17) se incluye como referencia en el dashboard.

Toda la metodología (D1–D17), incluyendo definición de exceso, features, tuning y evaluación, está en [`docs/decisiones_proyecto.md`](docs/decisiones_proyecto.md).

## Artefactos

- `foco_models.joblib` — Bundle `{cod_mpio: {municipio, logistic:{model,scaler,features}, xgboost:{model,scaler,features,best_params}}}`.
- `panel_municipal_mensual.csv` — Panel mensual 2007-2024 × 3 municipios (648 filas).
- `predicciones_test.csv` — Predicciones cacheadas baseline/logística/XGBoost para 2020-2024.
- `foco_meta.py` — Metadata compartida (coords, deptos, thresholds 0.3/0.6).

## Instalación

Requiere el entorno conda `dashboard_dengue`:

```bash
conda activate dashboard_dengue
pip install -r requirements.txt
```

## Ejecución

**Dashboard:**

```bash
streamlit run app.py
```

Disponible en `http://localhost:8501`.

**API REST:**

```bash
uvicorn api:app --reload
```

Endpoints en `http://localhost:8000`:

- `GET /health` — Estado del bundle y thresholds.
- `GET /municipios` — Lista los 3 focos con metadata.
- `GET /features?cod_mpio=23855&model_type=xgboost` — Features esperadas por el modelo.
- `POST /predict` — Body `{cod_mpio, model_type, features:{...}}`.

Documentación interactiva en `http://localhost:8000/docs`.

## Funcionalidades del dashboard

- Selector de municipio foco y de modelo (XGBoost por defecto, Logística, Baseline).
- Mapa con los 3 municipios coloreados según nivel de alerta del periodo.
- Serie temporal 2007-2024 con marcadores de exceso real y predicho (test 2020-2024).
- Curva de probabilidad del modelo activo en el test.
- Panel de riesgo: probabilidad, nivel, métricas (Precision/Recall/F1/Accuracy) y variables del periodo.
- Descarga CSV de la serie del municipio activo.

## Documentación del Reporte (Extracto)

**Fuentes del tablero desarrollada:**
> Repositorio principal: https://github.com/jhoneduardmoreno/dashboard_dengue  
> Tecnologías: Streamlit 1.30.0, scikit-learn 1.3.0 + joblib, Plotly  
> Integración modelo: model_loader.py carga logistic_dengue.pkl desde MLflow  
> Ejecución: `pip install -r requirements.txt && streamlit run app.py`

**Estado actual:** Prototipo funcional para Proyecto Despliegue de Soluciones.
Se despliega bajo un ambiente EC2 en AWS el cual se expone con una IP pública.

## Proyecto

MAIA — Universidad de los Andes  
Proyecto Desarrollo de Soluciones — Microproyecto Entrega 3 — 2026
