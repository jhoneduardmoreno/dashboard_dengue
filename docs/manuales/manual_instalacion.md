# Sistema de Alerta Temprana de Dengue — Colombia

Dashboard interactivo para la visualización y predicción de exceso epidémico de dengue a nivel municipal, acompañado de una API REST para consultas programáticas.

---

## Requisitos previos

| Requisito | Versión mínima | Notas |
|-----------|---------------|-------|
| Python | 3.9+ | Necesario para instalación local |
| Git | cualquiera | Para clonar el repositorio |
| Docker y Docker Compose | (opcional) | Alternativa a la instalación local |

Los archivos del modelo (`logistic_regression.joblib`) y el dataset (`panel_municipal_mensual.csv`) ya están incluidos en el repositorio.

---

## Opción A: Instalación local

### 1. Clonar el repositorio

```bash
git clone https://github.com/jhoneduardmoreno/dashboard_dengue.git
cd dashboard_dengue
```

### 2. Crear y activar un entorno virtual

**Linux / macOS:**

```bash
python -m venv venv
source venv/bin/activate
```

**Windows:**

```bash
python -m venv venv
venv\Scripts\activate
```

### 3. Instalar dependencias

Dependencias del dashboard:

```bash
pip install -r requirements.txt
```

Dependencias de la API:

```bash
pip install -r requirements_api.txt
```

### 4. Ejecutar el dashboard

```bash
streamlit run app.py
```

El dashboard estará disponible en `http://localhost:8501`.

### 5. Ejecutar la API (en otra terminal)

```bash
uvicorn api:app --host 0.0.0.0 --port 8000
```

La API estará disponible en `http://localhost:8000`.

---

## Opción B: Instalación con Docker

### Requisitos

- Docker
- Docker Compose

### Comando

```bash
docker compose up --build
```

Esto levanta dos servicios:

| Servicio | Puerto | URL |
|----------|--------|-----|
| Dashboard (Streamlit) | 8501 | `http://localhost:8501` |
| API (FastAPI) | 8000 | `http://localhost:8000` |

Para ejecutar en segundo plano:

```bash
docker compose up --build -d
```

Para detener los servicios:

```bash
docker compose down
```

---

## Estructura del proyecto

```
dashboard_dengue/
├── app.py                        # Dashboard Streamlit
├── api.py                        # API REST (FastAPI)
├── requirements.txt              # Dependencias del dashboard
├── requirements_api.txt          # Dependencias de la API
├── logistic_regression.joblib    # Modelo de regresión logística
├── panel_municipal_mensual.csv   # Dataset municipal mensual
├── Dockerfile.streamlit          # Imagen Docker del dashboard
├── Dockerfile.api                # Imagen Docker de la API
├── docker-compose.yml            # Orquestación de servicios
└── manuales/                     # Manuales del proyecto
```

---

## Verificación de la instalación

1. **Dashboard:** Abrir `http://localhost:8501` en el navegador. Verificar que el mapa de alertas se carga correctamente.
2. **API:** Abrir `http://localhost:8000/health` en el navegador o ejecutar:

```bash
curl http://localhost:8000/health
```

Si ambos servicios responden correctamente, la instalación fue exitosa.

