import streamlit as st
import requests
import pandas as pd
from urllib.parse import quote_plus
from sqlalchemy import create_engine 

from functions.coddir import coddir

@st.cache_data(show_spinner=False)
def getlatlng(direccion):
    latitud,longitud,barmanpre = getlatlngfromcatastro(direccion)
    if latitud is None or longitud is None:
        api_key  = st.secrets['API_KEY']
        direccion_codificada = quote_plus(direccion)
        url      = f"https://maps.googleapis.com/maps/api/geocode/json?address={direccion_codificada}&key={api_key}"
        response = requests.get(url)
        data     = response.json()
    
        if data['status'] == 'OK':
            latitud  = data['results'][0]['geometry']['location']['lat']
            longitud = data['results'][0]['geometry']['location']['lng']
    return latitud, longitud, barmanpre

@st.cache_data(show_spinner=False)
def getlatlngfromcatastro(direccion):
    latitud,longitud,barmanpre = [None]*3
    if isinstance(direccion, str):
        user     = st.secrets["user_bigdata"]
        password = st.secrets["password_bigdata"]
        host     = st.secrets["host_bigdata_lectura"]
        schema   = st.secrets["schema_bigdata"]
        engine   = create_engine(f'mysql+mysqlconnector://{user}:{password}@{host}/{schema}')
            
        fcoddir = coddir(direccion)
        data    = pd.read_sql_query(f"SELECT barmanpre, latitud,longitud FROM bigdata.data_bogota_catastro WHERE coddir='{fcoddir}'" , engine)
        engine.dispose()
        
        if not data.empty and 'latitud' in data and 'longitud' in data:
            latitud  = data['latitud'].median()
            longitud = data['longitud'].median()
        if not data.empty and 'barmanpre' in data:
            barmanpre = list(data['barmanpre'].unique())
    return latitud,longitud,barmanpre
