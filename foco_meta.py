"""Metadatos compartidos de los 3 municipios foco (D1 — decisiones_proyecto.md)."""

FOCO_META: dict[str, dict] = {
    "23855": {
        "municipio": "Valencia",
        "depto": "Córdoba",
        "region": "Caribe",
        "lat": 8.26,
        "lon": -76.15,
    },
    "47288": {
        "municipio": "Fundación",
        "depto": "Magdalena",
        "region": "Sierra Nevada",
        "lat": 10.52,
        "lon": -74.18,
    },
    "95025": {
        "municipio": "El Retorno",
        "depto": "Guaviare",
        "region": "Amazonía",
        "lat": 2.33,
        "lon": -72.63,
    },
}

THRESHOLDS = {"riesgo": 0.3, "alerta": 0.6}

MODEL_TYPES = ["logistic", "xgboost"]
