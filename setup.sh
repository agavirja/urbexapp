#!/bin/bash

# Crear la carpeta de configuración si no existe
mkdir -p ~/.streamlit/

# Crear config.toml con la configuración correcta de CORS y XSRF
cat <<EOL > ~/.streamlit/config.toml
[server]
headless = true
enableCORS = false
enableXsrfProtection = false
port = $PORT

[browser]
gatherUsageStats = false
EOL

# Instalar dependencias si es necesario
pip install --no-cache-dir --upgrade streamlit