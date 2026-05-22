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
