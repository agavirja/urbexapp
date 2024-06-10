import streamlit as st
import pandas as pd
from sqlalchemy import create_engine 
from streamlit_option_menu import option_menu
from bs4 import BeautifulSoup

from modulos._lotes_descripcion_combinacionlote import main as _descripcion_combinacionlote
from modulos._lotes_desarrollo_busqueda_pdfreport import main as _lotes_busqueda_pdfreport
from data.data_estudio_mercado_general import main as _estudio_mercado_parcial

def main(code=None):

    default_index = 0
    #-------------------------------------------------------------------------#
    # Header
    selectedmod = option_menu(None, ["Lotes", "Estudio de mercado","Reporte PDF","Nueva búsqueda"], 
        default_index=default_index, orientation="horizontal",icons=['hexagon','magic','file-earmark-pdf','arrow-counterclockwise'], 
        styles={
            "nav-link-selected": {"background-color": "#A16CFF"},
        })
        
    precuso,latitud,longitud = getlatlngPrecuso(code)
    
    if "Lotes" in selectedmod:
        _descripcion_combinacionlote(code)
    
    elif "Estudio de mercado" in selectedmod:
        _estudio_mercado_parcial(code=None,latitud=latitud,longitud=longitud,precuso=precuso) # barmanpre
  
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
def getlatlngPrecuso(code):
    
    user     = st.secrets["user_bigdata"]
    password = st.secrets["password_bigdata"]
    host     = st.secrets["host_bigdata_lectura"]
    schema   = st.secrets["schema_bigdata"]
    engine   = create_engine(f'mysql+mysqlconnector://{user}:{password}@{host}/{schema}')

    precuso,latitud,longitud = [None]*3
    try: 
        lista       = str(code).split('|')
        query       = "','".join(lista)
        query       = f" id IN ('{query}')"   
        datapredios = pd.read_sql_query(f"SELECT barmanpre FROM  bigdata.bogota_consolidacion_lotes_2000 WHERE {query}" , engine)
    
        if not datapredios.empty:
            barmanprelist = datapredios['barmanpre'].str.split('|')
            barmanprelist = [codigo for sublist in barmanprelist for codigo in sublist]
            barmanprelist = list(set(barmanprelist))
    
            query = "','".join(barmanprelist)
            query = f" barmanpre IN ('{query}')"   
            dataprecuso = pd.read_sql_query(f"SELECT precuso,latitud,longitud FROM  bigdata.bogota_catastro_compacta_precuso WHERE {query}" , engine)

            if not dataprecuso.empty:
                precuso  = list(dataprecuso['precuso'].unique())
                latitud  = dataprecuso['latitud'].mean()
                longitud = dataprecuso['longitud'].mean()
    except: pass
    return precuso,latitud,longitud

if __name__ == "__main__":
    main()
