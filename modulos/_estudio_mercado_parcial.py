import streamlit as st
import pandas as pd
from streamlit_js_eval import streamlit_js_eval
from streamlit_vertical_slider import vertical_slider
from sqlalchemy import create_engine 

from data.circle_polygon import circle_polygon
from data.reporte_analisis_mercado import main as reporte_analisis_mercado

def main(code=None,latitud=None,longitud=None,precuso=None):
    
    #-------------------------------------------------------------------------#
    # Latitud y longitud
    if latitud is None and longitud is None and code is not None: 
        latitud, longitud, precuso = latlngFrombarmanpre(code)
    
    polygon = None           
    metros  = 500
    if (isinstance(latitud, float) or isinstance(latitud, int)) or (isinstance(longitud, float) or isinstance(longitud, int)):
        polygon  = str(circle_polygon(metros,latitud,longitud))

    if polygon is not None:
        barmanpre = None
        if isinstance(code,str) and code!="":
            barmanpre = code.split('|')
        elif isinstance(code,list): 
            barmanpre = code.copy()
        reporte_analisis_mercado(polygon=polygon,precuso=precuso,barmanpreref=barmanpre,maxmetros=metros,tipo='radio')
        
@st.cache_data(show_spinner=False)
def latlngFrombarmanpre(barmanpre):
    user     = st.secrets["user_bigdata"]
    password = st.secrets["password_bigdata"]
    host     = st.secrets["host_bigdata_lectura"]
    schema   = st.secrets["schema_bigdata"]
    engine   = create_engine(f'mysql+mysqlconnector://{user}:{password}@{host}/{schema}')
    
    latitud  = None
    longitud = None
    precuso  = None
    
    if isinstance(barmanpre, str):
        barmanpre = barmanpre.split('|')
    
    if isinstance(barmanpre, list) and barmanpre!=[]:
        lista = "','".join(barmanpre)
        query = f" barmanpre IN ('{lista}')"
        datacatastro = pd.read_sql_query(f"SELECT latitud,longitud FROM  bigdata.data_bogota_catastro WHERE {query}" , engine)
        if not datacatastro.empty:
            latitud  = datacatastro['latitud'].median()
            longitud = datacatastro['longitud'].median()

        dataprecuso = pd.read_sql_query(f"SELECT distinct(precuso) as precuso FROM  bigdata.bogota_catastro_compacta_precuso WHERE {query}" , engine)
        if not dataprecuso.empty:
            precuso = list(dataprecuso['precuso'].unique())
            
    return latitud,longitud,precuso
