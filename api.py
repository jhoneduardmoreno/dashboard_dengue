"""
SAT Dengue — API REST para predicción de exceso epidémico (3 municipios foco).

Modelos per-municipio (D1, D5): Regresión Logística y XGBoost para los 3 focos
(Valencia 23855, Fundación 47288, El Retorno 95025). Bundle: `foco_models.joblib`.

Ejecutar con:
    uvicorn api:app --reload
"""

from contextlib import asynccontextmanager
from typing import Literal

import joblib
import numpy as np
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from foco_meta import FOCO_META, MODEL_TYPES, THRESHOLDS

_data: dict = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    bundle = joblib.load("data/foco_models.joblib")
    bundle_keys = set(bundle.keys())
    meta_keys = set(FOCO_META.keys())
    if bundle_keys != meta_keys:
        raise RuntimeError(
            f"Inconsistencia bundle vs FOCO_META: bundle={bundle_keys} meta={meta_keys}"
        )
    _data["bundle"] = bundle
    yield
    _data.clear()


app = FastAPI(
    title="SAT Dengue API",
    description=(
        "Predicción de exceso epidémico de dengue para los 3 municipios foco "
        "del microproyecto MAIA. Cada municipio tiene su propio par de modelos "
        "(logistic, xgboost) entrenados sobre 2007–2019 y evaluados en 2020–2024. "
        "Ver docs/decisiones_proyecto.md (D1–D17)."
    ),
    version="3.0.0",
    lifespan=lifespan,
    root_path="/api",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

ModelType = Literal["logistic", "xgboost"]


class PredictRequest(BaseModel):
    cod_mpio: str = Field(..., description="Código DIVIPOLA del municipio foco")
    model_type: ModelType = Field("xgboost", description="Modelo a aplicar")
    features: dict[str, float] = Field(
        ..., description="Diccionario con las features del modelo (orden libre)."
    )


class PredictResponse(BaseModel):
    cod_mpio: str
    municipio: str
    model_type: ModelType
    probabilidad_exceso: float
    nivel_alerta: str


class MunicipioInfo(BaseModel):
    cod_mpio: str
    municipio: str
    depto: str
    region: str
    lat: float
    lon: float


class HealthResponse(BaseModel):
    status: str
    municipios: list[str]
    model_types: list[str]
    thresholds: dict[str, float]


class FeaturesResponse(BaseModel):
    cod_mpio: str
    model_type: ModelType
    features: list[str]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_artefactos(cod_mpio: str, model_type: str) -> dict:
    bundle = _data["bundle"]
    if cod_mpio not in bundle:
        raise HTTPException(
            status_code=404,
            detail=f"cod_mpio '{cod_mpio}' no está en el bundle. Disponibles: {list(bundle.keys())}",
        )
    if model_type not in bundle[cod_mpio]:
        raise HTTPException(
            status_code=400,
            detail=f"model_type '{model_type}' no disponible. Opciones: {MODEL_TYPES}",
        )
    return bundle[cod_mpio][model_type]


def _nivel_alerta(prob: float) -> str:
    if prob >= THRESHOLDS["alerta"]:
        return "Alerta"
    if prob >= THRESHOLDS["riesgo"]:
        return "Riesgo"
    return "Normal"


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@app.get("/health", response_model=HealthResponse)
def health():
    return HealthResponse(
        status="ok",
        municipios=sorted(_data["bundle"].keys()),
        model_types=MODEL_TYPES,
        thresholds=THRESHOLDS,
    )


@app.get("/municipios", response_model=list[MunicipioInfo])
def municipios():
    return [
        MunicipioInfo(
            cod_mpio=cod,
            municipio=m["municipio"],
            depto=m["depto"],
            region=m["region"],
            lat=m["lat"],
            lon=m["lon"],
        )
        for cod, m in FOCO_META.items()
    ]


@app.get("/features", response_model=FeaturesResponse)
def features(cod_mpio: str, model_type: ModelType = "xgboost"):
    art = _get_artefactos(cod_mpio, model_type)
    return FeaturesResponse(cod_mpio=cod_mpio, model_type=model_type, features=art["features"])


@app.post("/predict", response_model=PredictResponse)
def predict(req: PredictRequest):
    art = _get_artefactos(req.cod_mpio, req.model_type)
    feature_names = art["features"]

    missing = [f for f in feature_names if f not in req.features]
    if missing:
        raise HTTPException(
            status_code=422,
            detail=f"Faltan features para el modelo {req.cod_mpio}/{req.model_type}: {missing}",
        )

    values = [req.features[f] for f in feature_names]
    X = np.array(values, dtype=float).reshape(1, -1)
    X_scaled = art["scaler"].transform(X)
    prob = float(art["model"].predict_proba(X_scaled)[0, 1])

    return PredictResponse(
        cod_mpio=req.cod_mpio,
        municipio=FOCO_META[req.cod_mpio]["municipio"],
        model_type=req.model_type,
        probabilidad_exceso=round(prob, 6),
        nivel_alerta=_nivel_alerta(prob),
    )
