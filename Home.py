import streamlit as st

st.set_page_config(layout='wide',page_icon="https://iconsapp.nyc3.digitaloceanspaces.com/urbex_favicon.png")

# streamlit run D:\Dropbox\Empresa\Urbex\proceso\_APP_nueva_version\Home.py
# https://streamlit.io/
# pipreqs --encoding utf-8 "D:\Dropbox\Empresa\Urbex\proceso\_APP_nueva_version"

#------------#
# Powersheel #

# Archivos donde esta la palabra "urbextestapp\.streamlit\.app" o "urbextestapp\.streamlit\.app"
# Get-ChildItem -Path D:\Dropbox\Empresa\Urbex\_APP_heroku -Recurse -Filter *.py | ForEach-Object { if (Get-Content $_.FullName | Select-String -Pattern 'localhost:8501' -Quiet) { $_.FullName } }

# Reemplazar "localhost:8501" por "localhost:8501" o al reves en los archivos donde esta la palabra
# Get-ChildItem -Path D:\Dropbox\Empresa\Urbex\_APP_heroku -Recurse -Filter *.py | ForEach-Object {(Get-Content $_.FullName) | ForEach-Object {$_ -replace 'localhost:8501', 'localhost:8501'} | Set-Content $_.FullName}
# Get-ChildItem -Path 'C:\Users\LENOVO T14\Documents\GitHub\urbexapp' -Recurse -Filter *.py | ForEach-Object {(Get-Content $_.FullName) | ForEach-Object {$_ -replace 'localhost:8501', 'www.urbex.com.co'} | Set-Content $_.FullName}