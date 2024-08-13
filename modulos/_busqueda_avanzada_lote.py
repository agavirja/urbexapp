import streamlit as st
import pandas as pd
from sqlalchemy import create_engine 
from streamlit_option_menu import option_menu
from bs4 import BeautifulSoup

from modulos._lotes_descripcion_combinacionlote import main as _descripcion_combinacionlote
from modulos._lotes_desarrollo_busqueda_pdfreport import main as _lotes_busqueda_pdfreport
from modulos._cabida_lotes import main as _cabida_lotes

from modulos._estudio_mercado_parcial import main as _estudio_mercado_parcial

def main(code=None,precuso=None,selectoption=None):

    col1,col2,col3 = st.columns([6,1,1])
    with col2:
        st.image('https://iconsapp.nyc3.digitaloceanspaces.com/urbex_negativo.png',width=200)
        
    default_index = 0
    if isinstance(selectoption,str) and selectoption!="":
        if 'edm' in selectoption:
            default_index = 2
            
    #-------------------------------------------------------------------------#
    # Header
    selectedmod = option_menu(None, ["Descripción","Cabida","Estudio de mercado","Reporte PDF","Nueva búsqueda"], 
        default_index=default_index, orientation="horizontal",icons=['info-circle','magic','graph-up','file-earmark-pdf','search'], 
        styles={
            "nav-link-selected": {"background-color": "#A16CFF"},
        })
        
    precuso_output,latitud,longitud = getlatlngPrecuso(code)
    
    if precuso is None or isinstance(precuso,list) and precuso==[]:
        precuso = precuso_output.copy()
    
    if "Descripción" in selectedmod:
        _descripcion_combinacionlote(code)
        
    elif "Cabida" in selectedmod:
        _cabida_lotes(code)
  
    elif "Estudio de mercado" in selectedmod:
        _estudio_mercado_parcial(code=code,latitud=latitud,longitud=longitud,precuso=precuso)
  
    elif "Reporte PDF" in selectedmod:
        _lotes_busqueda_pdfreport(code=code,latitud=latitud,longitud=longitud,precuso=precuso)
        
    elif "Nueva búsqueda" in selectedmod:
        
        col1,col2,col3 = st.columns([0.15,0.2,0.65])
        style_button_dir = """
        <style>
        .custom-button {
            display: inline-block;
            padding: 10px 20px;
            background-color: #A16CFF;
            color: #ffffff; 
            font-weight: bold;
            text-decoration: none;
            border-radius: 10px;
            width: 100%;
            border: none;
            cursor: pointer;
            text-align: center;
            letter-spacing: 1px;
            box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
            margin-bottom: 20px;
        }
        .custom-button:visited {
            color: #ffffff;
        }
        </style>
        """
        nombre = '¿Seguro quiere salir de está página?'
        html = f"""<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">{style_button_dir}</head><body><a href="http://www.urbex.com.co/Busqueda_avanzada?token={st.session_state.token}" class="custom-button" target="_self">{nombre}</a></body></html>"""
        html = BeautifulSoup(html, 'html.parser')
        with col2:
            st.markdown(html, unsafe_allow_html=True)
            
@st.cache_data(show_spinner=False)
def getlatlngPrecuso(code=None):
    
    user     = st.secrets["user_bigdata"]
    password = st.secrets["password_bigdata"]
    host     = st.secrets["host_bigdata_lectura"]
    schema   = st.secrets["schema_bigdata"]
    engine   = create_engine(f'mysql+mysqlconnector://{user}:{password}@{host}/{schema}')

    precuso,latitud,longitud = [None]*3
    if code is not None and isinstance(code,str):
        lista       = code.split('|')
        query       = "','".join(lista)
        query       = f" barmanpre IN ('{query}')"
        dataprecuso = pd.read_sql_query(f"SELECT precuso,latitud,longitud FROM  bigdata.bogota_catastro_compacta_precuso WHERE {query}" , engine)
        if not dataprecuso.empty:
            precuso  = list(dataprecuso['precuso'].unique())
            latitud  = dataprecuso['latitud'].mean()
            longitud = dataprecuso['longitud'].mean()
    return precuso,latitud,longitud

if __name__ == "__main__":
    main()
