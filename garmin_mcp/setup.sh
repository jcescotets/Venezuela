#!/bin/bash
# Setup script for Garmin MCP Server
# Run this on your local machine to configure everything

set -e

echo "=== Garmin MCP Setup para Claude Code ==="
echo ""

# 1. Install dependencies
echo "[1/3] Instalando dependencias..."
pip install garth fitparse pydantic "mcp[cli]>=1.0.0"

# 2. Authenticate with Garmin Connect
echo ""
echo "[2/3] Autenticando con Garmin Connect..."

read -p "Email de Garmin Connect: " GARMIN_EMAIL
read -s -p "Password de Garmin Connect: " GARMIN_PASSWORD
echo ""

python3 -c "
import garth, os
client = garth.Client(domain='garmin.com')
client.login('${GARMIN_EMAIL}', '${GARMIN_PASSWORD}')
token_dir = os.path.expanduser('~/.garth')
os.makedirs(token_dir, exist_ok=True)
client.dump(token_dir)
print('Tokens guardados en ~/.garth/')
"

# 3. Register MCP server in Claude Code
echo ""
echo "[3/3] Registrando servidor MCP en Claude Code..."

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SERVER_PATH="${SCRIPT_DIR}/server.py"

claude mcp add garmin-mcp -- python3 "$SERVER_PATH"

echo ""
echo "=== Setup completado! ==="
echo "Reinicia Claude Code y pregunta por tus datos de Garmin."
echo "Ejemplo: 'Muéstrame mis últimas 10 actividades'"
