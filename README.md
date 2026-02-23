# 🦟 Sistema de Alerta Temprana de Dengue — Colombia

Dashboard interactivo para la visualización y predicción de exceso epidémico de dengue a nivel municipal.

## Requisitos

- Python 3.9+
- Archivos necesarios en la misma carpeta:
  - `app.py` — Código del dashboard
  - `panel_municipal_mensual.csv` — Dataset del proyecto
  - `logistic_regression.joblib` — Modelo entrenado

## Instalación

```bash
pip install -r requirements.txt
```

## Ejecución

```bash
streamlit run app.py
```

El dashboard estará disponible en `http://localhost:8501`

## Funcionalidades

- **Filtros interactivos**: Por año, mes, departamento y municipio
- **Tabla de alertas**: Top 15 municipios con mayor probabilidad de exceso
- **Serie temporal**: Evolución de casos regulares y graves con probabilidad de exceso
- **Variables climáticas**: Temperatura, precipitación, NDVI y punto de rocío
- **Panel de riesgo**: Detalle de probabilidad para municipio seleccionado

## Documentación del Reporte (Extracto)

**Fuentes del tablero desarrollada:**
> Repositorio principal: https://github.com/jhoneduardmoreno/dashboard_dengue  
> Tecnologías: Streamlit 1.30.0, scikit-learn 1.3.0 + joblib, Plotly  
> Integración modelo: model_loader.py carga logistic_dengue.pkl desde MLflow  
> Ejecución: `pip install -r requirements.txt && streamlit run app.py`

**Estado actual:** Prototipo funcional para Entrega 2 Microproyecto PDS.

## Proyecto

MAIA — Universidad de los Andes  
Proyecto Desarrollo de Soluciones — Microproyecto  
2026
