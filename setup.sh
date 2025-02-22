#!/bin/bash

mkdir -p ~/.streamlit/

echo "\
[general]\n\
email = \"agavirja+1@gmail.com\"\n\
" > ~/.streamlit/credentials.toml

echo "\
[server]\n\
headless = true\n\
enableCORS=false\n\
enableXsrfProtection=false\n\
port = $PORT\n\
\n\
[browser]\n\
gatherUsageStats=false\n\
" > ~/.streamlit/config.toml

pip install --no-cache-dir --upgrade streamlit