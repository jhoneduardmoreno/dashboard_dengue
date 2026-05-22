# Diseño: Despliegue Docker + SSL en DigitalOcean (sin dominio)

**Fecha:** 2026-05-21  
**Droplet:** `root@104.248.121.223` (Ubuntu, aprovisionamiento desde cero)  
**Repo:** `https://github.com/jhoneduardmoreno/dashboard_dengue.git` (público)

---

## Arquitectura

```
Internet (:80, :443)
        │
        ▼
┌───────────────────────────────────────────┐
│              Droplet Ubuntu 22.04          │
│                                           │
│  ┌─────────────────────────────────────┐  │
│  │         nginx (contenedor)          │  │
│  │  SSL termination · reverse proxy    │  │
│  └──────────┬──────────────┬───────────┘  │
│             │              │              │
│   ┌─────────▼──┐  ┌────────▼─────────┐   │
│   │ dashboard  │  │       api        │   │
│   │ streamlit  │  │     fastapi      │   │
│   │  :8501     │  │      :8000       │   │
│   └────────────┘  └──────────────────┘   │
│                                           │
│  Red interna Docker: dengue_net           │
└───────────────────────────────────────────┘
```

## Servicios Docker

| Servicio    | Imagen base       | Puerto interno | Expuesto al host |
|-------------|-------------------|----------------|------------------|
| `nginx`     | `nginx:alpine`    | 80, 443        | 80, 443          |
| `dashboard` | `python:3.11-slim`| 8501           | no               |
| `api`       | `python:3.11-slim`| 8000           | no               |

`dashboard` y `api` no exponen puertos al host — solo accesibles dentro de `dengue_net`. Nginx es el único punto de entrada externo.

## SSL

- **Tipo:** certificado autofirmado (self-signed), RSA 2048, validez 365 días
- **Generado en el servidor** con `openssl` durante el primer despliegue
- **Almacenado en** `nginx/certs/server.crt` y `nginx/certs/server.key`
- **No se commitea** al repo (cubierto por `.gitignore`)
- El navegador mostrará advertencia de seguridad la primera vez — comportamiento esperado con IP sin dominio

**Decisión:** No se usa Certbot/Let's Encrypt porque requiere nombre de dominio para validación HTTP/DNS.

## Rutas Nginx

| URL                                  | Destino          |
|--------------------------------------|------------------|
| `https://104.248.121.223/`           | `dashboard:8501` |
| `https://104.248.121.223/api/`       | `api:8000`       |
| `http://104.248.121.223/` (cualquier)| redirect 301 → HTTPS |

## Archivos a crear/modificar

```
dashboard_dengue/
├── docker-compose.yml          ← reemplazar (agrega nginx + red interna)
├── Dockerfile.streamlit        ← corregir (foco_models.joblib, predicciones_test.csv, foco_meta.py)
├── Dockerfile.api              ← corregir (foco_models.joblib, foco_meta.py)
├── nginx/
│   └── nginx.conf              ← nuevo
├── deploy.sh                   ← nuevo (script de aprovisionamiento + despliegue)
└── .gitignore                  ← agregar nginx/certs/
```

`nginx/certs/` se crea en el servidor, no en el repo.

## Script de despliegue (`deploy.sh`)

Ejecutado una sola vez en el droplet vía SSH. Pasos:

1. `apt update && apt upgrade -y`
2. Instalar Docker CE + Docker Compose plugin
3. Instalar git
4. Configurar `ufw`: permitir 22, 80, 443; habilitar firewall
5. `git clone https://github.com/jhoneduardmoreno/dashboard_dengue.git`
6. Generar certificado autofirmado en `nginx/certs/`
7. `docker compose up -d --build`

## Configuración Nginx (`nginx/nginx.conf`)

```nginx
events {}

http {
    # Redirect HTTP → HTTPS
    server {
        listen 80;
        return 301 https://$host$request_uri;
    }

    server {
        listen 443 ssl;
        ssl_certificate     /etc/nginx/certs/server.crt;
        ssl_certificate_key /etc/nginx/certs/server.key;

        # Dashboard Streamlit
        location / {
            proxy_pass http://dashboard:8501;
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection "upgrade";
            proxy_set_header Host $host;
        }

        # API FastAPI
        location /api/ {
            proxy_pass http://api:8000/;
            proxy_set_header Host $host;
        }
    }
}
```

**WebSocket:** Los headers `Upgrade` y `Connection` son necesarios para que Streamlit funcione correctamente detrás de Nginx.

## Ajuste FastAPI para proxy

FastAPI genera URLs internas en su OpenAPI schema usando la raíz `/`. Detrás de un proxy en `/api/`, los links de `/docs` quedarían rotos. Solución: inicializar la app con `root_path="/api"` en `api.py`:

```python
app = FastAPI(..., root_path="/api")
```

Esto hace que `/api/docs` funcione correctamente.

## Correcciones a Dockerfiles existentes

Los Dockerfiles actuales referencian `logistic_regression.joblib` (archivo obsoleto). Deben actualizarse para copiar:

- `foco_models.joblib`
- `foco_meta.py`
- `panel_municipal_mensual.csv` (solo Streamlit)
- `predicciones_test.csv` (solo Streamlit)

## Firewall

| Puerto | Protocolo | Motivo              |
|--------|-----------|---------------------|
| 22     | TCP       | SSH                 |
| 80     | TCP       | HTTP → redirect HTTPS |
| 443    | TCP       | HTTPS               |

Puertos 8000 y 8501 permanecen cerrados al exterior.

## Criterios de éxito

- `https://104.248.121.223/` carga el dashboard Streamlit
- `https://104.248.121.223/api/docs` carga la documentación FastAPI
- HTTP redirige a HTTPS automáticamente
- Servicios se reinician solos si el droplet se reinicia (`restart: unless-stopped`)
