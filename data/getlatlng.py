import streamlit as st
import requests
from urllib.parse import quote_plus

@st.cache_data
def getlatlng(direccion):
    api_key  = st.secrets['API_KEY']
    latitud  = None
    longitud = None
    direccion_codificada = quote_plus(direccion)
    url      = f"https://maps.googleapis.com/maps/api/geocode/json?address={direccion_codificada}&key={api_key}"
    response = requests.get(url)
    data     = response.json()

    if data['status'] == 'OK':
        latitud  = data['results'][0]['geometry']['location']['lat']
        longitud = data['results'][0]['geometry']['location']['lng']
    return latitud, longitud
