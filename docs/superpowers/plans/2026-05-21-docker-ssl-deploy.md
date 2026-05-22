# Docker + SSL Deployment Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Desplegar el dashboard SAT Dengue (Streamlit + FastAPI) en el droplet `104.248.121.223` usando Docker + Nginx con SSL autofirmado, accesible en `https://104.248.121.223/`.

**Architecture:** Nginx termina SSL en puerto 443 y hace proxy hacia dos contenedores internos: `dashboard:8501` (Streamlit) y `api:8000` (FastAPI). HTTP redirige a HTTPS. Los contenedores `dashboard` y `api` no exponen puertos al host. Todo orquestado con Docker Compose en una red interna `dengue_net`.

**Tech Stack:** Docker CE, Docker Compose plugin, Nginx Alpine, Python 3.11-slim, openssl (cert autofirmado), ufw (firewall)

---

## Mapa de archivos

| Archivo | Acción | Responsabilidad |
|---|---|---|
| `Dockerfile.streamlit` | Modificar | Copiar archivos correctos del proyecto |
| `Dockerfile.api` | Modificar | Copiar archivos correctos + agregar xgboost |
| `requirements_api.txt` | Modificar | Agregar xgboost (necesario para cargar el bundle) |
| `docker-compose.yml` | Reemplazar | Orquestar 3 servicios + red interna |
| `nginx/nginx.conf` | Crear | SSL termination + reverse proxy + WebSocket |
| `api.py` | Modificar línea 39 | Agregar `root_path="/api"` para proxy correcto |
| `.gitignore` | Modificar | Ignorar `nginx/certs/` |
| `deploy.sh` | Crear | Script de aprovisionamiento + despliegue en el servidor |

---

## Task 1: Corregir Dockerfile.streamlit

**Files:**
- Modify: `Dockerfile.streamlit`

Los Dockerfiles actuales copian `logistic_regression.joblib` (archivo obsoleto). El proyecto usa `foco_models.joblib`, `predicciones_test.csv` y `foco_meta.py`.

- [ ] **Step 1: Reemplazar Dockerfile.streamlit**

Contenido completo:

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py .
COPY foco_meta.py .
COPY panel_municipal_mensual.csv .
COPY predicciones_test.csv .
COPY foco_models.joblib .

EXPOSE 8501

CMD ["streamlit", "run", "app.py", \
     "--server.port", "8501", \
     "--server.address", "0.0.0.0", \
     "--server.headless", "true"]
```

- [ ] **Step 2: Commit**

```bash
git add Dockerfile.streamlit
git commit -m "fix: update Dockerfile.streamlit to use foco_models bundle"
```

---

## Task 2: Corregir Dockerfile.api y requirements_api.txt

**Files:**
- Modify: `Dockerfile.api`
- Modify: `requirements_api.txt`

El bundle `foco_models.joblib` contiene `XGBClassifier`. Sin `xgboost` en el contenedor, `joblib.load()` fallará al deserializar.

- [ ] **Step 1: Actualizar requirements_api.txt**

Contenido completo:

```
fastapi
uvicorn
joblib
scikit-learn
numpy
pandas
xgboost
```

- [ ] **Step 2: Reemplazar Dockerfile.api**

Contenido completo:

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements_api.txt .
RUN pip install --no-cache-dir -r requirements_api.txt

COPY api.py .
COPY foco_meta.py .
COPY foco_models.joblib .

EXPOSE 8000

CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8000"]
```

- [ ] **Step 3: Commit**

```bash
git add Dockerfile.api requirements_api.txt
git commit -m "fix: add xgboost to api deps and update Dockerfile.api"
```

---

## Task 3: Agregar root_path a FastAPI

**Files:**
- Modify: `api.py:39-49`

FastAPI genera sus URLs internas (OpenAPI schema, `/docs`, `/redoc`) usando la raíz `/`. Detrás de Nginx en `/api/`, los links quedan rotos. `root_path="/api"` le indica a FastAPI su prefijo real.

- [ ] **Step 1: Verificar que el test falla (sin root_path)**

El `/docs` de FastAPI bajo proxy generaría links incorrectos. Esto se verifica visualmente tras el despliegue, pero primero aseguramos el cambio en código.

- [ ] **Step 2: Agregar root_path en api.py**

Localizar el bloque `app = FastAPI(...)` en `api.py` (líneas 39-49) y agregar `root_path="/api"`:

```python
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
```

- [ ] **Step 3: Commit**

```bash
git add api.py
git commit -m "fix: add root_path=/api for FastAPI behind Nginx proxy"
```

---

## Task 4: Crear nginx/nginx.conf

**Files:**
- Create: `nginx/nginx.conf`

Nginx hace SSL termination y proxy hacia los servicios internos. Los headers `Upgrade` y `Connection` son obligatorios para que Streamlit funcione vía WebSocket. `proxy_read_timeout 86400` evita que Nginx cierre las conexiones WebSocket de larga duración.

- [ ] **Step 1: Crear directorio y archivo**

Crear `nginx/nginx.conf` con el contenido:

```nginx
events {
    worker_connections 1024;
}

http {
    # Redirigir todo HTTP → HTTPS
    server {
        listen 80;
        server_name _;
        return 301 https://$host$request_uri;
    }

    server {
        listen 443 ssl;
        server_name _;

        ssl_certificate     /etc/nginx/certs/server.crt;
        ssl_certificate_key /etc/nginx/certs/server.key;
        ssl_protocols       TLSv1.2 TLSv1.3;
        ssl_ciphers         HIGH:!aNULL:!MD5;

        # Dashboard Streamlit (WebSocket necesario)
        location / {
            proxy_pass         http://dashboard:8501;
            proxy_http_version 1.1;
            proxy_set_header   Upgrade $http_upgrade;
            proxy_set_header   Connection "upgrade";
            proxy_set_header   Host $host;
            proxy_set_header   X-Real-IP $remote_addr;
            proxy_set_header   X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header   X-Forwarded-Proto https;
            proxy_read_timeout 86400;
        }

        # API FastAPI
        location /api/ {
            proxy_pass       http://api:8000/;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto https;
        }
    }
}
```

- [ ] **Step 2: Commit**

```bash
git add nginx/nginx.conf
git commit -m "feat: add nginx reverse proxy config with SSL and WebSocket support"
```

---

## Task 5: Reemplazar docker-compose.yml

**Files:**
- Modify: `docker-compose.yml`

Agrega el servicio `nginx`, la red interna `dengue_net`, y elimina la exposición de puertos de `dashboard` y `api` al host.

- [ ] **Step 1: Reemplazar docker-compose.yml**

Contenido completo:

```yaml
services:
  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf:ro
      - ./nginx/certs:/etc/nginx/certs:ro
    depends_on:
      - dashboard
      - api
    restart: unless-stopped
    networks:
      - dengue_net

  dashboard:
    build:
      context: .
      dockerfile: Dockerfile.streamlit
    restart: unless-stopped
    networks:
      - dengue_net

  api:
    build:
      context: .
      dockerfile: Dockerfile.api
    restart: unless-stopped
    networks:
      - dengue_net

networks:
  dengue_net:
    driver: bridge
```

- [ ] **Step 2: Commit**

```bash
git add docker-compose.yml
git commit -m "feat: add nginx service and internal network to docker-compose"
```

---

## Task 6: Actualizar .gitignore

**Files:**
- Modify: `.gitignore`

Los certificados se generan en el servidor y no deben commitearse al repo.

- [ ] **Step 1: Agregar entrada en .gitignore**

Agregar al final del archivo `.gitignore`:

```
nginx/certs/
```

- [ ] **Step 2: Commit**

```bash
git add .gitignore
git commit -m "chore: ignore generated SSL certs"
```

---

## Task 7: Crear deploy.sh

**Files:**
- Create: `deploy.sh`

Script ejecutado **una sola vez** en el droplet vía SSH. Aprovisiona el servidor desde cero, clona el repo, genera el certificado y lanza los contenedores.

- [ ] **Step 1: Crear deploy.sh**

```bash
#!/bin/bash
set -e

echo "==> Actualizando sistema..."
apt-get update -y && apt-get upgrade -y

echo "==> Instalando Docker CE..."
apt-get install -y ca-certificates curl gnupg
install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg \
  | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
chmod a+r /etc/apt/keyrings/docker.gpg
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
  https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo "$VERSION_CODENAME") stable" \
  | tee /etc/apt/sources.list.d/docker.list > /dev/null
apt-get update -y
apt-get install -y docker-ce docker-ce-cli containerd.io \
                   docker-buildx-plugin docker-compose-plugin

echo "==> Instalando git..."
apt-get install -y git

echo "==> Configurando firewall..."
ufw --force enable
ufw allow 22/tcp
ufw allow 80/tcp
ufw allow 443/tcp
ufw status

echo "==> Clonando repositorio..."
cd /opt
git clone https://github.com/jhoneduardmoreno/dashboard_dengue.git
cd dashboard_dengue

echo "==> Generando certificado SSL autofirmado..."
mkdir -p nginx/certs
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout nginx/certs/server.key \
  -out  nginx/certs/server.crt \
  -subj "/CN=104.248.121.223"

echo "==> Levantando servicios Docker..."
docker compose up -d --build

echo ""
echo "✓ Despliegue completo"
echo "  Dashboard: https://104.248.121.223/"
echo "  API docs:  https://104.248.121.223/api/docs"
echo ""
echo "Nota: El navegador mostrará advertencia de certificado autofirmado."
echo "Aceptar con 'Avanzado → Continuar'."
```

- [ ] **Step 2: Commit y push**

```bash
git add deploy.sh
git commit -m "feat: add server provisioning and deployment script"
git push origin main
```

---

## Task 8: Ejecutar despliegue en el droplet

**Prerequisito:** Tasks 1–7 pusheados a `main` en GitHub.

- [ ] **Step 1: Conectarse al droplet**

```bash
ssh root@104.248.121.223
```

- [ ] **Step 2: Descargar y ejecutar el script**

```bash
curl -fsSL https://raw.githubusercontent.com/jhoneduardmoreno/dashboard_dengue/main/deploy.sh | bash
```

Tiempo esperado: ~5-10 minutos (instala Docker, clona repo, construye imágenes).

Output esperado al final:
```
✓ Despliegue completo
  Dashboard: https://104.248.121.223/
  API docs:  https://104.248.121.223/api/docs
```

- [ ] **Step 3: Verificar que los contenedores están corriendo**

```bash
cd /opt/dashboard_dengue
docker compose ps
```

Output esperado:
```
NAME                    STATUS          PORTS
dashboard_dengue-nginx-1      Up    0.0.0.0:80->80/tcp, 0.0.0.0:443->443/tcp
dashboard_dengue-dashboard-1  Up
dashboard_dengue-api-1        Up
```

---

## Task 9: Smoke tests

Verificar que todos los endpoints responden correctamente.

- [ ] **Step 1: Test HTTP → HTTPS redirect**

```bash
curl -I http://104.248.121.223/
```

Output esperado:
```
HTTP/1.1 301 Moved Permanently
Location: https://104.248.121.223/
```

- [ ] **Step 2: Test dashboard Streamlit**

```bash
curl -k -I https://104.248.121.223/
```

Output esperado:
```
HTTP/1.1 200 OK
```

(`-k` ignora advertencia de certificado autofirmado)

- [ ] **Step 3: Test API health**

```bash
curl -k https://104.248.121.223/api/health
```

Output esperado:
```json
{"status": "ok", "bundle_loaded": true, "thresholds": {"riesgo": 0.3, "alerta": 0.6}}
```

- [ ] **Step 4: Test API docs**

```bash
curl -k -I https://104.248.121.223/api/docs
```

Output esperado:
```
HTTP/1.1 200 OK
```

- [ ] **Step 5: Test predicción (opcional — verificar end-to-end)**

```bash
curl -k -X POST https://104.248.121.223/api/predict \
  -H "Content-Type: application/json" \
  -d '{
    "cod_mpio": "23855",
    "model_type": "xgboost",
    "features": {
      "temperatura_c": 28.5, "precipitacion_mm": 120.0, "ndvi": 0.45,
      "dewpoint_c": 22.0,
      "temperatura_c_lag1": 28.0, "precipitacion_mm_lag1": 110.0,
      "ndvi_lag1": 0.44, "dewpoint_c_lag1": 21.5,
      "temperatura_c_lag2": 27.5, "precipitacion_mm_lag2": 100.0,
      "ndvi_lag2": 0.43, "dewpoint_c_lag2": 21.0,
      "temperatura_c_lag3": 27.0, "precipitacion_mm_lag3": 90.0,
      "ndvi_lag3": 0.42, "dewpoint_c_lag3": 20.5,
      "temperatura_c_ma3": 28.0, "precipitacion_mm_ma3": 107.0,
      "ndvi_ma3": 0.44, "dewpoint_c_ma3": 21.7,
      "casos_total_lag1": 15, "casos_total_lag2": 12, "casos_total_lag3": 10,
      "incidencia_x100k_lag1": 25.0, "incidencia_x100k_lag2": 20.0,
      "incidencia_x100k_lag3": 17.0,
      "mes_sin": 0.5, "mes_cos": 0.866
    }
  }'
```

Output esperado: JSON con `probabilidad`, `pred`, `nivel_alerta`.

---

## Troubleshooting

**Ver logs de un servicio:**
```bash
docker compose logs -f nginx
docker compose logs -f dashboard
docker compose logs -f api
```

**Reiniciar todo:**
```bash
docker compose down && docker compose up -d --build
```

**Verificar puertos abiertos:**
```bash
ufw status
ss -tlnp | grep -E '80|443'
```
